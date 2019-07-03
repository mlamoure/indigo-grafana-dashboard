import React, { PureComponent } from 'react';
import { hot } from 'react-hot-loader';
import { connect } from 'react-redux';
import moment from 'moment';
import { RawTimeRange, TimeRange, LogLevel, TimeZone, AbsoluteTimeRange } from '@grafana/ui';

import { ExploreId, ExploreItemState } from 'app/types/explore';
import { LogsModel, LogsDedupStrategy } from 'app/core/logs_model';
import { StoreState } from 'app/types';

import { toggleLogs, changeDedupStrategy, changeTime } from './state/actions';
import Logs from './Logs';
import Panel from './Panel';
import { toggleLogLevelAction } from 'app/features/explore/state/actionTypes';
import { deduplicatedLogsSelector, exploreItemUIStateSelector } from 'app/features/explore/state/selectors';
import { getTimeZone } from '../profile/state/selectors';

interface LogsContainerProps {
  exploreId: ExploreId;
  loading: boolean;
  logsHighlighterExpressions?: string[];
  logsResult?: LogsModel;
  dedupedResult?: LogsModel;
  onClickLabel: (key: string, value: string) => void;
  onStartScanning: () => void;
  onStopScanning: () => void;
  range: TimeRange;
  timeZone: TimeZone;
  scanning?: boolean;
  scanRange?: RawTimeRange;
  showingLogs: boolean;
  toggleLogs: typeof toggleLogs;
  toggleLogLevelAction: typeof toggleLogLevelAction;
  changeDedupStrategy: typeof changeDedupStrategy;
  dedupStrategy: LogsDedupStrategy;
  hiddenLogLevels: Set<LogLevel>;
  width: number;
  changeTime: typeof changeTime;
}

export class LogsContainer extends PureComponent<LogsContainerProps> {
  onChangeTime = (absRange: AbsoluteTimeRange) => {
    const { exploreId, timeZone, changeTime } = this.props;
    const range = {
      from: timeZone.isUtc ? moment.utc(absRange.from) : moment(absRange.from),
      to: timeZone.isUtc ? moment.utc(absRange.to) : moment(absRange.to),
    };

    changeTime(exploreId, range);
  };
  onClickLogsButton = () => {
    this.props.toggleLogs(this.props.exploreId, this.props.showingLogs);
  };

  handleDedupStrategyChange = (dedupStrategy: LogsDedupStrategy) => {
    this.props.changeDedupStrategy(this.props.exploreId, dedupStrategy);
  };

  hangleToggleLogLevel = (hiddenLogLevels: Set<LogLevel>) => {
    const { exploreId } = this.props;
    this.props.toggleLogLevelAction({
      exploreId,
      hiddenLogLevels,
    });
  };

  render() {
    const {
      exploreId,
      loading,
      logsHighlighterExpressions,
      logsResult,
      dedupedResult,
      onClickLabel,
      onStartScanning,
      onStopScanning,
      range,
      timeZone,
      showingLogs,
      scanning,
      scanRange,
      width,
      hiddenLogLevels,
    } = this.props;

    return (
      <Panel label="Logs" loading={loading} isOpen={showingLogs} onToggle={this.onClickLogsButton}>
        <Logs
          dedupStrategy={this.props.dedupStrategy || LogsDedupStrategy.none}
          data={logsResult}
          dedupedData={dedupedResult}
          exploreId={exploreId}
          highlighterExpressions={logsHighlighterExpressions}
          loading={loading}
          onChangeTime={this.onChangeTime}
          onClickLabel={onClickLabel}
          onStartScanning={onStartScanning}
          onStopScanning={onStopScanning}
          onDedupStrategyChange={this.handleDedupStrategyChange}
          onToggleLogLevel={this.hangleToggleLogLevel}
          range={range}
          timeZone={timeZone}
          scanning={scanning}
          scanRange={scanRange}
          width={width}
          hiddenLogLevels={hiddenLogLevels}
        />
      </Panel>
    );
  }
}

function mapStateToProps(state: StoreState, { exploreId }) {
  const explore = state.explore;
  const item: ExploreItemState = explore[exploreId];
  const { logsHighlighterExpressions, logsResult, queryTransactions, scanning, scanRange, range } = item;
  const loading = queryTransactions.some(qt => qt.resultType === 'Logs' && !qt.done);
  const { showingLogs, dedupStrategy } = exploreItemUIStateSelector(item);
  const hiddenLogLevels = new Set(item.hiddenLogLevels);
  const dedupedResult = deduplicatedLogsSelector(item);
  const timeZone = getTimeZone(state.user);

  return {
    loading,
    logsHighlighterExpressions,
    logsResult,
    scanning,
    scanRange,
    showingLogs,
    range,
    timeZone,
    dedupStrategy,
    hiddenLogLevels,
    dedupedResult,
  };
}

const mapDispatchToProps = {
  toggleLogs,
  changeDedupStrategy,
  toggleLogLevelAction,
  changeTime,
};

export default hot(module)(
  connect(
    mapStateToProps,
    mapDispatchToProps
  )(LogsContainer)
);
