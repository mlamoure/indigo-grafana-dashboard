import _ from 'lodash';

import {
  CompletionItem,
  CompletionItemGroup,
  LanguageProvider,
  TypeaheadInput,
  TypeaheadOutput,
} from 'app/types/explore';

import { parseSelector, processLabels, processHistogramLabels } from './language_utils';
import PromqlSyntax, { FUNCTIONS, RATE_RANGES } from './promql';
import { dateTime } from '@grafana/data';

const DEFAULT_KEYS = ['job', 'instance'];
const EMPTY_SELECTOR = '{}';
const HISTORY_ITEM_COUNT = 5;
const HISTORY_COUNT_CUTOFF = 1000 * 60 * 60 * 24; // 24h

const wrapLabel = (label: string) => ({ label });

const setFunctionKind = (suggestion: CompletionItem): CompletionItem => {
  suggestion.kind = 'function';
  return suggestion;
};

export function addHistoryMetadata(item: CompletionItem, history: any[]): CompletionItem {
  const cutoffTs = Date.now() - HISTORY_COUNT_CUTOFF;
  const historyForItem = history.filter(h => h.ts > cutoffTs && h.query === item.label);
  const count = historyForItem.length;
  const recent = historyForItem[0];
  let hint = `Queried ${count} times in the last 24h.`;
  if (recent) {
    const lastQueried = dateTime(recent.ts).fromNow();
    hint = `${hint} Last queried ${lastQueried}.`;
  }
  return {
    ...item,
    documentation: hint,
  };
}

export default class PromQlLanguageProvider extends LanguageProvider {
  histogramMetrics?: string[];
  timeRange?: { start: number; end: number };
  labelKeys?: { [index: string]: string[] }; // metric -> [labelKey,...]
  labelValues?: { [index: string]: { [index: string]: string[] } }; // metric -> labelKey -> [labelValue,...]
  metrics?: string[];
  startTask: Promise<any>;

  constructor(datasource: any, initialValues?: any) {
    super();

    this.datasource = datasource;
    this.histogramMetrics = [];
    this.timeRange = { start: 0, end: 0 };
    this.labelKeys = {};
    this.labelValues = {};
    this.metrics = [];

    Object.assign(this, initialValues);
  }
  // Strip syntax chars
  cleanText = (s: string) => s.replace(/[{}[\]="(),!~+\-*/^%]/g, '').trim();

  getSyntax() {
    return PromqlSyntax;
  }

  request = async (url: string) => {
    try {
      const res = await this.datasource.metadataRequest(url);
      const body = await (res.data || res.json());

      return body.data;
    } catch (error) {
      console.error(error);
    }

    return [];
  };

  start = () => {
    if (!this.startTask) {
      this.startTask = this.fetchMetrics();
    }
    return this.startTask;
  };

  fetchMetrics = async () => {
    this.metrics = await this.fetchMetricNames();
    this.processHistogramMetrics(this.metrics);

    return Promise.resolve([]);
  };

  fetchMetricNames = async (): Promise<string[]> => {
    return this.request('/api/v1/label/__name__/values');
  };

  processHistogramMetrics = (data: string[]) => {
    const { values } = processHistogramLabels(data);

    if (values && values['__name__']) {
      this.histogramMetrics = values['__name__'].slice().sort();
    }
  };

  // Keep this DOM-free for testing
  provideCompletionItems({ prefix, wrapperClasses, text, value }: TypeaheadInput, context?: any): TypeaheadOutput {
    // Local text properties
    const empty = value.document.text.length === 0;
    const selectedLines = value.document.getTextsAtRangeAsArray(value.selection);
    const currentLine = selectedLines.length === 1 ? selectedLines[0] : null;
    const nextCharacter = currentLine ? currentLine.text[value.selection.anchorOffset] : null;

    // Syntax spans have 3 classes by default. More indicate a recognized token
    const tokenRecognized = wrapperClasses.length > 3;
    // Non-empty prefix, but not inside known token
    const prefixUnrecognized = prefix && !tokenRecognized;
    // Prevent suggestions in `function(|suffix)`
    const noSuffix = !nextCharacter || nextCharacter === ')';
    // Empty prefix is safe if it does not immediately folllow a complete expression and has no text after it
    const safeEmptyPrefix = prefix === '' && !text.match(/^[\]})\s]+$/) && noSuffix;
    // About to type next operand if preceded by binary operator
    const isNextOperand = text.match(/[+\-*/^%]/);

    // Determine candidates by CSS context
    if (_.includes(wrapperClasses, 'context-range')) {
      // Suggestions for metric[|]
      return this.getRangeCompletionItems();
    } else if (_.includes(wrapperClasses, 'context-labels')) {
      // Suggestions for metric{|} and metric{foo=|}, as well as metric-independent label queries like {|}
      return this.getLabelCompletionItems.apply(this, arguments);
    } else if (_.includes(wrapperClasses, 'context-aggregation')) {
      // Suggestions for sum(metric) by (|)
      return this.getAggregationCompletionItems.apply(this, arguments);
    } else if (empty) {
      // Suggestions for empty query field
      return this.getEmptyCompletionItems(context || {});
    } else if (prefixUnrecognized || safeEmptyPrefix || isNextOperand) {
      // Show term suggestions in a couple of scenarios
      return this.getTermCompletionItems();
    }

    return {
      suggestions: [],
    };
  }

  getEmptyCompletionItems(context: any): TypeaheadOutput {
    const { history } = context;
    let suggestions: CompletionItemGroup[] = [];

    if (history && history.length > 0) {
      const historyItems = _.chain(history)
        .map((h: any) => h.query.expr)
        .filter()
        .uniq()
        .take(HISTORY_ITEM_COUNT)
        .map(wrapLabel)
        .map((item: CompletionItem) => addHistoryMetadata(item, history))
        .value();

      suggestions.push({
        prefixMatch: true,
        skipSort: true,
        label: 'History',
        items: historyItems,
      });
    }

    const termCompletionItems = this.getTermCompletionItems();
    suggestions = [...suggestions, ...termCompletionItems.suggestions];

    return { suggestions };
  }

  getTermCompletionItems(): TypeaheadOutput {
    const { metrics } = this;
    const suggestions: CompletionItemGroup[] = [];

    suggestions.push({
      prefixMatch: true,
      label: 'Functions',
      items: FUNCTIONS.map(setFunctionKind),
    });

    if (metrics && metrics.length > 0) {
      suggestions.push({
        label: 'Metrics',
        items: metrics.map(wrapLabel),
      });
    }
    return { suggestions };
  }

  getRangeCompletionItems(): TypeaheadOutput {
    return {
      context: 'context-range',
      suggestions: [
        {
          label: 'Range vector',
          items: [...RATE_RANGES],
        },
      ],
    };
  }

  roundToMinutes(seconds: number): number {
    return Math.floor(seconds / 60);
  }

  timeRangeChanged(): boolean {
    const dsRange = this.datasource.getTimeRange();
    return (
      this.roundToMinutes(dsRange.end) !== this.roundToMinutes(this.timeRange.end) ||
      this.roundToMinutes(dsRange.start) !== this.roundToMinutes(this.timeRange.start)
    );
  }

  getAggregationCompletionItems({ value }: TypeaheadInput): TypeaheadOutput {
    const refresher: Promise<any> = null;
    const suggestions: CompletionItemGroup[] = [];

    // Stitch all query lines together to support multi-line queries
    let queryOffset;
    const queryText = value.document.getBlocks().reduce((text: string, block: any) => {
      const blockText = block.getText();
      if (value.anchorBlock.key === block.key) {
        // Newline characters are not accounted for but this is irrelevant
        // for the purpose of extracting the selector string
        queryOffset = value.anchorOffset + text.length;
      }
      text += blockText;
      return text;
    }, '');

    // Try search for selector part on the left-hand side, such as `sum (m) by (l)`
    const openParensAggregationIndex = queryText.lastIndexOf('(', queryOffset);
    let openParensSelectorIndex = queryText.lastIndexOf('(', openParensAggregationIndex - 1);
    let closeParensSelectorIndex = queryText.indexOf(')', openParensSelectorIndex);

    // Try search for selector part of an alternate aggregation clause, such as `sum by (l) (m)`
    if (openParensSelectorIndex === -1) {
      const closeParensAggregationIndex = queryText.indexOf(')', queryOffset);
      closeParensSelectorIndex = queryText.indexOf(')', closeParensAggregationIndex + 1);
      openParensSelectorIndex = queryText.lastIndexOf('(', closeParensSelectorIndex);
    }

    const result = {
      refresher,
      suggestions,
      context: 'context-aggregation',
    };

    // Suggestions are useless for alternative aggregation clauses without a selector in context
    if (openParensSelectorIndex === -1) {
      return result;
    }

    let selectorString = queryText.slice(openParensSelectorIndex + 1, closeParensSelectorIndex);

    // Range vector syntax not accounted for by subsequent parse so discard it if present
    selectorString = selectorString.replace(/\[[^\]]+\]$/, '');

    const selector = parseSelector(selectorString, selectorString.length - 2).selector;

    const labelKeys = this.labelKeys[selector];
    if (labelKeys && !this.timeRangeChanged()) {
      suggestions.push({ label: 'Labels', items: labelKeys.map(wrapLabel) });
    } else {
      result.refresher = this.fetchSeriesLabels(selector);
    }

    return result;
  }

  getLabelCompletionItems({ text, wrapperClasses, labelKey, value }: TypeaheadInput): TypeaheadOutput {
    let context: string;
    let refresher: Promise<any> = null;
    const suggestions: CompletionItemGroup[] = [];
    const line = value.anchorBlock.getText();
    const cursorOffset: number = value.anchorOffset;

    // Get normalized selector
    let selector;
    let parsedSelector;
    try {
      parsedSelector = parseSelector(line, cursorOffset);
      selector = parsedSelector.selector;
    } catch {
      selector = EMPTY_SELECTOR;
    }
    const containsMetric = selector.indexOf('__name__=') > -1;
    const existingKeys = parsedSelector ? parsedSelector.labelKeys : [];

    if ((text && text.match(/^!?=~?/)) || _.includes(wrapperClasses, 'attr-value')) {
      // Label values
      if (labelKey && this.labelValues[selector] && this.labelValues[selector][labelKey]) {
        const labelValues = this.labelValues[selector][labelKey];
        context = 'context-label-values';
        suggestions.push({
          label: `Label values for "${labelKey}"`,
          items: labelValues.map(wrapLabel),
        });
      }
    } else {
      // Label keys
      const labelKeys = this.labelKeys[selector] || (containsMetric ? null : DEFAULT_KEYS);
      if (labelKeys) {
        const possibleKeys = _.difference(labelKeys, existingKeys);
        if (possibleKeys.length > 0) {
          context = 'context-labels';
          suggestions.push({ label: `Labels`, items: possibleKeys.map(wrapLabel) });
        }
      }
    }

    // Query labels for selector
    if (selector && (!this.labelValues[selector] || this.timeRangeChanged())) {
      if (selector === EMPTY_SELECTOR) {
        // Query label values for default labels
        refresher = Promise.all(DEFAULT_KEYS.map(key => this.fetchLabelValues(key)));
      } else {
        refresher = this.fetchSeriesLabels(selector, !containsMetric);
      }
    }

    return { context, refresher, suggestions };
  }

  fetchLabelValues = async (key: string) => {
    try {
      const data = await this.request(`/api/v1/label/${key}/values`);
      const existingValues = this.labelValues[EMPTY_SELECTOR];
      const values = {
        ...existingValues,
        [key]: data,
      };
      this.labelValues[EMPTY_SELECTOR] = values;
    } catch (e) {
      console.error(e);
    }
  };

  fetchSeriesLabels = async (name: string, withName?: boolean) => {
    try {
      const tRange = this.datasource.getTimeRange();
      const data = await this.request(`/api/v1/series?match[]=${name}&start=${tRange['start']}&end=${tRange['end']}`);
      const { keys, values } = processLabels(data, withName);
      this.labelKeys[name] = keys;
      this.labelValues[name] = values;
      this.timeRange = tRange;
    } catch (e) {
      console.error(e);
    }
  };
}
