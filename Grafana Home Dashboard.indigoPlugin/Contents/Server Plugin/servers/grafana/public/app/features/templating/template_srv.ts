import kbn from 'app/core/utils/kbn';
import _ from 'lodash';
import { deprecationWarning, ScopedVars, textUtil, TimeRange } from '@grafana/data';
import { getFilteredVariables, getVariables, getVariableWithName } from '../variables/state/selectors';
import { getConfig } from 'app/core/config';
import { variableRegex } from './utils';
import { isAdHoc } from '../variables/guard';
import { VariableModel } from './types';
import { setTemplateSrv, TemplateSrv as BaseTemplateSrv } from '@grafana/runtime';
import { variableAdapters } from '../variables/adapters';

function luceneEscape(value: string) {
  return value.replace(/([\!\*\+\-\=<>\s\&\|\(\)\[\]\{\}\^\~\?\:\\/"])/g, '\\$1');
}

interface FieldAccessorCache {
  [key: string]: (obj: any) => any;
}

export interface TemplateSrvDependencies {
  getFilteredVariables: typeof getFilteredVariables;
  getVariables: typeof getVariables;
  getVariableWithName: typeof getVariableWithName;
}

const runtimeDependencies: TemplateSrvDependencies = {
  getFilteredVariables,
  getVariables,
  getVariableWithName,
};

export class TemplateSrv implements BaseTemplateSrv {
  private _variables: any[];
  private regex = variableRegex;
  private index: any = {};
  private grafanaVariables: any = {};
  private builtIns: any = {};
  private timeRange?: TimeRange | null = null;
  private fieldAccessorCache: FieldAccessorCache = {};

  constructor(private dependencies: TemplateSrvDependencies = runtimeDependencies) {
    this.builtIns['__interval'] = { text: '1s', value: '1s' };
    this.builtIns['__interval_ms'] = { text: '100', value: '100' };
    this._variables = [];
  }

  init(variables: any, timeRange?: TimeRange) {
    this._variables = variables;
    this.timeRange = timeRange;
    this.updateIndex();
  }

  getBuiltInIntervalValue() {
    return this.builtIns.__interval.value;
  }

  /**
   * @deprecated: this instance variable should not be used and will be removed in future releases
   *
   * Use getVariables function instead
   */
  get variables(): any[] {
    deprecationWarning('template_srv.ts', 'variables', 'getVariables');
    return this.getVariables();
  }

  getVariables(): VariableModel[] {
    if (getConfig().featureToggles.newVariables) {
      return this.dependencies.getVariables();
    }

    return this._variables;
  }

  updateIndex() {
    const existsOrEmpty = (value: any) => value || value === '';

    this.index = this._variables.reduce((acc, currentValue) => {
      if (currentValue.current && (currentValue.current.isNone || existsOrEmpty(currentValue.current.value))) {
        acc[currentValue.name] = currentValue;
      }
      return acc;
    }, {});

    if (this.timeRange) {
      const from = this.timeRange.from.valueOf().toString();
      const to = this.timeRange.to.valueOf().toString();

      this.index = {
        ...this.index,
        ['__from']: {
          current: { value: from, text: from },
        },
        ['__to']: {
          current: { value: to, text: to },
        },
      };
    }
  }

  updateTimeRange(timeRange: TimeRange) {
    this.timeRange = timeRange;
    this.updateIndex();
  }

  variableInitialized(variable: any) {
    this.index[variable.name] = variable;
  }

  getAdhocFilters(datasourceName: string) {
    let filters: any = [];

    for (const variable of this.getAdHocVariables()) {
      if (variable.datasource === null || variable.datasource === datasourceName) {
        filters = filters.concat(variable.filters);
      } else if (variable.datasource.indexOf('$') === 0) {
        if (this.replace(variable.datasource) === datasourceName) {
          filters = filters.concat(variable.filters);
        }
      }
    }

    return filters;
  }

  luceneFormat(value: any) {
    if (typeof value === 'string') {
      return luceneEscape(value);
    }
    if (value instanceof Array && value.length === 0) {
      return '__empty__';
    }
    const quotedValues = _.map(value, val => {
      return '"' + luceneEscape(val) + '"';
    });
    return '(' + quotedValues.join(' OR ') + ')';
  }

  // encode string according to RFC 3986; in contrast to encodeURIComponent()
  // also the sub-delims "!", "'", "(", ")" and "*" are encoded;
  // unicode handling uses UTF-8 as in ECMA-262.
  encodeURIComponentStrict(str: string) {
    return encodeURIComponent(str).replace(/[!'()*]/g, c => {
      return (
        '%' +
        c
          .charCodeAt(0)
          .toString(16)
          .toUpperCase()
      );
    });
  }

  formatValue(value: any, format: any, variable: any) {
    // for some scopedVars there is no variable
    variable = variable || {};

    if (typeof format === 'function') {
      return format(value, variable, this.formatValue);
    }

    switch (format) {
      case 'regex': {
        if (typeof value === 'string') {
          return kbn.regexEscape(value);
        }

        const escapedValues = _.map(value, kbn.regexEscape);
        if (escapedValues.length === 1) {
          return escapedValues[0];
        }
        return '(' + escapedValues.join('|') + ')';
      }
      case 'lucene': {
        return this.luceneFormat(value);
      }
      case 'pipe': {
        if (typeof value === 'string') {
          return value;
        }
        return value.join('|');
      }
      case 'distributed': {
        if (typeof value === 'string') {
          return value;
        }
        return this.distributeVariable(value, variable.name);
      }
      case 'csv': {
        if (_.isArray(value)) {
          return value.join(',');
        }
        return value;
      }
      case 'html': {
        if (_.isArray(value)) {
          return textUtil.escapeHtml(value.join(', '));
        }
        return textUtil.escapeHtml(value);
      }
      case 'json': {
        return JSON.stringify(value);
      }
      case 'percentencode': {
        // like glob, but url escaped
        if (_.isArray(value)) {
          return this.encodeURIComponentStrict('{' + value.join(',') + '}');
        }
        return this.encodeURIComponentStrict(value);
      }
      case 'singlequote': {
        // escape single quotes with backslash
        const regExp = new RegExp(`'`, 'g');
        if (_.isArray(value)) {
          return _.map(value, v => `'${_.replace(v, regExp, `\\'`)}'`).join(',');
        }
        return `'${_.replace(value, regExp, `\\'`)}'`;
      }
      case 'doublequote': {
        // escape double quotes with backslash
        const regExp = new RegExp('"', 'g');
        if (_.isArray(value)) {
          return _.map(value, v => `"${_.replace(v, regExp, '\\"')}"`).join(',');
        }
        return `"${_.replace(value, regExp, '\\"')}"`;
      }
      case 'sqlstring': {
        // escape single quotes by pairing them
        const regExp = new RegExp(`'`, 'g');
        if (_.isArray(value)) {
          return _.map(value, v => `'${_.replace(v, regExp, "''")}'`).join(',');
        }
        return `'${_.replace(value, regExp, "''")}'`;
      }
      default: {
        if (_.isArray(value) && value.length > 1) {
          return '{' + value.join(',') + '}';
        }
        return value;
      }
    }
  }

  setGrafanaVariable(name: string, value: any) {
    this.grafanaVariables[name] = value;
  }

  setGlobalVariable(name: string, variable: any) {
    this.index = {
      ...this.index,
      [name]: {
        current: variable,
      },
    };
  }

  getVariableName(expression: string) {
    this.regex.lastIndex = 0;
    const match = this.regex.exec(expression);
    if (!match) {
      return null;
    }
    const variableName = match.slice(1).find(match => match !== undefined);
    return variableName;
  }

  variableExists(expression: string) {
    const name = this.getVariableName(expression);
    return name && this.getVariableAtIndex(name) !== void 0;
  }

  highlightVariablesAsHtml(str: string) {
    if (!str || !_.isString(str)) {
      return str;
    }

    str = _.escape(str);
    this.regex.lastIndex = 0;
    return str.replace(this.regex, (match, var1, var2, fmt2, var3) => {
      if (this.getVariableAtIndex(var1 || var2 || var3) || this.builtIns[var1 || var2 || var3]) {
        return '<span class="template-variable">' + match + '</span>';
      }
      return match;
    });
  }

  getAllValue(variable: any) {
    if (variable.allValue) {
      return variable.allValue;
    }
    const values = [];
    for (let i = 1; i < variable.options.length; i++) {
      values.push(variable.options[i].value);
    }
    return values;
  }

  getFieldAccessor(fieldPath: string) {
    const accessor = this.fieldAccessorCache[fieldPath];
    if (accessor) {
      return accessor;
    }

    return (this.fieldAccessorCache[fieldPath] = _.property(fieldPath));
  }

  getVariableValue(variableName: string, fieldPath: string | undefined, scopedVars: ScopedVars) {
    const scopedVar = scopedVars[variableName];
    if (!scopedVar) {
      return null;
    }

    if (fieldPath) {
      return this.getFieldAccessor(fieldPath)(scopedVar.value);
    }

    return scopedVar.value;
  }

  replace(target: string, scopedVars?: ScopedVars, format?: string | Function): string {
    if (!target) {
      return target;
    }

    this.regex.lastIndex = 0;

    return target.replace(this.regex, (match, var1, var2, fmt2, var3, fieldPath, fmt3) => {
      const variableName = var1 || var2 || var3;
      const variable = this.getVariableAtIndex(variableName);
      const fmt = fmt2 || fmt3 || format;

      if (scopedVars) {
        const value = this.getVariableValue(variableName, fieldPath, scopedVars);
        if (value !== null && value !== undefined) {
          return this.formatValue(value, fmt, variable);
        }
      }

      if (!variable) {
        return match;
      }

      const systemValue = this.grafanaVariables[variable.current.value];
      if (systemValue) {
        return this.formatValue(systemValue, fmt, variable);
      }

      let value = variable.current.value;
      if (this.isAllValue(value)) {
        value = this.getAllValue(variable);
        // skip formatting of custom all values
        if (variable.allValue) {
          return this.replace(value);
        }
      }

      if (fieldPath) {
        const fieldValue = this.getVariableValue(variableName, fieldPath, {
          [variableName]: { value: value, text: '' },
        });
        if (fieldValue !== null && fieldValue !== undefined) {
          return this.formatValue(fieldValue, fmt, variable);
        }
      }

      const res = this.formatValue(value, fmt, variable);
      return res;
    });
  }

  isAllValue(value: any) {
    return value === '$__all' || (Array.isArray(value) && value[0] === '$__all');
  }

  replaceWithText(target: string, scopedVars?: ScopedVars) {
    if (!target) {
      return target;
    }

    let variable;
    this.regex.lastIndex = 0;

    return target.replace(this.regex, (match: any, var1: any, var2: any, fmt2: any, var3: any) => {
      if (scopedVars) {
        const option = scopedVars[var1 || var2 || var3];
        if (option) {
          return option.text;
        }
      }

      variable = this.getVariableAtIndex(var1 || var2 || var3);
      if (!variable) {
        return match;
      }

      const value = this.grafanaVariables[variable.current.value];

      return typeof value === 'string' ? value : variable.current.text;
    });
  }

  fillVariableValuesForUrl = (params: any, scopedVars?: ScopedVars) => {
    _.each(this.getVariables(), variable => {
      if (scopedVars && scopedVars[variable.name] !== void 0) {
        if (scopedVars[variable.name].skipUrlSync) {
          return;
        }
        params['var-' + variable.name] = scopedVars[variable.name].value;
      } else {
        if (variable.skipUrlSync) {
          return;
        }
        params['var-' + variable.name] = variableAdapters.get(variable.type).getValueForUrl(variable);
      }
    });
  };

  distributeVariable(value: any, variable: any) {
    value = _.map(value, (val: any, index: number) => {
      if (index !== 0) {
        return variable + '=' + val;
      } else {
        return val;
      }
    });
    return value.join(',');
  }

  private getVariableAtIndex = (name: string): any => {
    if (!name) {
      return;
    }

    if (getConfig().featureToggles.newVariables && !this.index[name]) {
      return this.dependencies.getVariableWithName(name);
    }

    return this.index[name];
  };

  private getAdHocVariables = (): any[] => {
    if (getConfig().featureToggles.newVariables) {
      return this.dependencies.getFilteredVariables(isAdHoc);
    }
    if (Array.isArray(this._variables)) {
      return this._variables.filter(isAdHoc);
    }
    return [];
  };
}

// Expose the template srv
const srv = new TemplateSrv();
setTemplateSrv(srv);
export default srv;
