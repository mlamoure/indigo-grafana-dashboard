// Libraries
import React, { ComponentClass } from 'react';
import { hot } from 'react-hot-loader';
// @ts-ignore
import { connect } from 'react-redux';
import _ from 'lodash';
import { AutoSizer } from 'react-virtualized';

// Services & Utils
import store from 'app/core/store';

// Components
import { Alert } from './Error';
import ErrorBoundary from './ErrorBoundary';
import GraphContainer from './GraphContainer';
import LogsContainer from './LogsContainer';
import QueryRows from './QueryRows';
import TableContainer from './TableContainer';

// Actions
import {
  changeSize,
  initializeExplore,
  modifyQueries,
  scanStart,
  setQueries,
  refreshExplore,
  reconnectDatasource,
  updateTimeRange,
} from './state/actions';

// Types
import { RawTimeRange } from '@grafana/data';

import { DataQuery, ExploreStartPageProps, DataSourceApi, DataQueryError } from '@grafana/ui';
import {
  ExploreItemState,
  ExploreUrlState,
  ExploreId,
  ExploreUpdateState,
  ExploreUIState,
  ExploreMode,
} from 'app/types/explore';
import { StoreState } from 'app/types';
import {
  ensureQueries,
  DEFAULT_RANGE,
  DEFAULT_UI_STATE,
  getTimeRangeFromUrl,
  lastUsedDatasourceKeyForOrgId,
} from 'app/core/utils/explore';
import { Emitter } from 'app/core/utils/emitter';
import { ExploreToolbar } from './ExploreToolbar';
import { NoDataSourceCallToAction } from './NoDataSourceCallToAction';
import { FadeIn } from 'app/core/components/Animations/FadeIn';
import { getTimeZone } from '../profile/state/selectors';
import { ErrorContainer } from './ErrorContainer';
import { scanStopAction } from './state/actionTypes';

interface ExploreProps {
  StartPage?: ComponentClass<ExploreStartPageProps>;
  changeSize: typeof changeSize;
  datasourceError: string;
  datasourceInstance: DataSourceApi;
  datasourceLoading: boolean | null;
  datasourceMissing: boolean;
  exploreId: ExploreId;
  initializeExplore: typeof initializeExplore;
  initialized: boolean;
  modifyQueries: typeof modifyQueries;
  update: ExploreUpdateState;
  reconnectDatasource: typeof reconnectDatasource;
  refreshExplore: typeof refreshExplore;
  scanning?: boolean;
  scanRange?: RawTimeRange;
  scanStart: typeof scanStart;
  scanStopAction: typeof scanStopAction;
  setQueries: typeof setQueries;
  split: boolean;
  showingStartPage?: boolean;
  queryKeys: string[];
  initialDatasource: string;
  initialQueries: DataQuery[];
  initialRange: RawTimeRange;
  mode: ExploreMode;
  initialUI: ExploreUIState;
  queryErrors: DataQueryError[];
  isLive: boolean;
  updateTimeRange: typeof updateTimeRange;
}

/**
 * Explore provides an area for quick query iteration for a given datasource.
 * Once a datasource is selected it populates the query section at the top.
 * When queries are run, their results are being displayed in the main section.
 * The datasource determines what kind of query editor it brings, and what kind
 * of results viewers it supports. The state is managed entirely in Redux.
 *
 * SPLIT VIEW
 *
 * Explore can have two Explore areas side-by-side. This is handled in `Wrapper.tsx`.
 * Since there can be multiple Explores (e.g., left and right) each action needs
 * the `exploreId` as first parameter so that the reducer knows which Explore state
 * is affected.
 *
 * DATASOURCE REQUESTS
 *
 * A click on Run Query creates transactions for all DataQueries for all expanded
 * result viewers. New runs are discarding previous runs. Upon completion a transaction
 * saves the result. The result viewers construct their data from the currently existing
 * transactions.
 *
 * The result viewers determine some of the query options sent to the datasource, e.g.,
 * `format`, to indicate eventual transformations by the datasources' result transformers.
 */
export class Explore extends React.PureComponent<ExploreProps> {
  el: any;
  exploreEvents: Emitter;

  constructor(props: ExploreProps) {
    super(props);
    this.exploreEvents = new Emitter();
  }

  componentDidMount() {
    const { initialized, exploreId, initialDatasource, initialQueries, initialRange, mode, initialUI } = this.props;
    const width = this.el ? this.el.offsetWidth : 0;

    // initialize the whole explore first time we mount and if browser history contains a change in datasource
    if (!initialized) {
      this.props.initializeExplore(
        exploreId,
        initialDatasource,
        initialQueries,
        initialRange,
        mode,
        width,
        this.exploreEvents,
        initialUI
      );
    }
  }

  componentWillUnmount() {
    this.exploreEvents.removeAllListeners();
  }

  componentDidUpdate(prevProps: ExploreProps) {
    this.refreshExplore();
  }

  getRef = (el: any) => {
    this.el = el;
  };

  onChangeTime = (rawRange: RawTimeRange) => {
    const { updateTimeRange, exploreId } = this.props;

    updateTimeRange({ exploreId, rawRange });
  };

  // Use this in help pages to set page to a single query
  onClickExample = (query: DataQuery) => {
    this.props.setQueries(this.props.exploreId, [query]);
  };

  onClickLabel = (key: string, value: string) => {
    this.onModifyQueries({ type: 'ADD_FILTER', key, value });
  };

  onModifyQueries = (action: any, index?: number) => {
    const { datasourceInstance } = this.props;
    if (datasourceInstance && datasourceInstance.modifyQuery) {
      const modifier = (queries: DataQuery, modification: any) => datasourceInstance.modifyQuery(queries, modification);
      this.props.modifyQueries(this.props.exploreId, action, index, modifier);
    }
  };

  onResize = (size: { height: number; width: number }) => {
    this.props.changeSize(this.props.exploreId, size);
  };

  onStartScanning = () => {
    // Scanner will trigger a query
    this.props.scanStart(this.props.exploreId);
  };

  onStopScanning = () => {
    this.props.scanStopAction({ exploreId: this.props.exploreId });
  };

  refreshExplore = () => {
    const { exploreId, update } = this.props;

    if (update.queries || update.ui || update.range || update.datasource) {
      this.props.refreshExplore(exploreId);
    }
  };

  renderEmptyState = () => {
    return (
      <div className="explore-container">
        <NoDataSourceCallToAction />
      </div>
    );
  };

  onReconnect = (event: React.MouseEvent<HTMLButtonElement>) => {
    const { exploreId, reconnectDatasource } = this.props;

    event.preventDefault();
    reconnectDatasource(exploreId);
  };

  render() {
    const {
      StartPage,
      datasourceInstance,
      datasourceError,
      datasourceLoading,
      datasourceMissing,
      exploreId,
      showingStartPage,
      split,
      queryKeys,
      queryErrors,
      mode,
    } = this.props;
    const exploreClass = split ? 'explore explore-split' : 'explore';

    return (
      <div className={exploreClass} ref={this.getRef}>
        <ExploreToolbar exploreId={exploreId} onChangeTime={this.onChangeTime} />
        {datasourceLoading ? <div className="explore-container">Loading datasource...</div> : null}
        {datasourceMissing ? this.renderEmptyState() : null}

        <FadeIn duration={datasourceError ? 150 : 5} in={datasourceError ? true : false}>
          <div className="explore-container">
            <Alert
              message={`Error connecting to datasource: ${datasourceError}`}
              button={{ text: 'Reconnect', onClick: this.onReconnect }}
            />
          </div>
        </FadeIn>

        {datasourceInstance && (
          <div className="explore-container">
            <QueryRows exploreEvents={this.exploreEvents} exploreId={exploreId} queryKeys={queryKeys} />
            <ErrorContainer queryErrors={queryErrors} />
            <AutoSizer onResize={this.onResize} disableHeight>
              {({ width }) => {
                if (width === 0) {
                  return null;
                }

                return (
                  <main className="m-t-2" style={{ width }}>
                    <ErrorBoundary>
                      {showingStartPage && <StartPage onClickExample={this.onClickExample} />}
                      {!showingStartPage && (
                        <>
                          {mode === ExploreMode.Metrics && <GraphContainer width={width} exploreId={exploreId} />}
                          {mode === ExploreMode.Metrics && (
                            <TableContainer exploreId={exploreId} onClickCell={this.onClickLabel} />
                          )}
                          {mode === ExploreMode.Logs && (
                            <LogsContainer
                              width={width}
                              exploreId={exploreId}
                              onClickLabel={this.onClickLabel}
                              onStartScanning={this.onStartScanning}
                              onStopScanning={this.onStopScanning}
                            />
                          )}
                        </>
                      )}
                    </ErrorBoundary>
                  </main>
                );
              }}
            </AutoSizer>
          </div>
        )}
      </div>
    );
  }
}

function mapStateToProps(state: StoreState, { exploreId }: ExploreProps) {
  const explore = state.explore;
  const { split } = explore;
  const item: ExploreItemState = explore[exploreId];
  const timeZone = getTimeZone(state.user);
  const {
    StartPage,
    datasourceError,
    datasourceInstance,
    datasourceLoading,
    datasourceMissing,
    initialized,
    showingStartPage,
    queryKeys,
    urlState,
    update,
    queryErrors,
    isLive,
    supportedModes,
    mode,
  } = item;

  const { datasource, queries, range: urlRange, mode: urlMode, ui } = (urlState || {}) as ExploreUrlState;
  const initialDatasource = datasource || store.get(lastUsedDatasourceKeyForOrgId(state.user.orgId));
  const initialQueries: DataQuery[] = ensureQueries(queries);
  const initialRange = urlRange ? getTimeRangeFromUrl(urlRange, timeZone).raw : DEFAULT_RANGE;

  let newMode: ExploreMode;
  if (supportedModes.length) {
    const urlModeIsValid = supportedModes.includes(urlMode);
    const modeStateIsValid = supportedModes.includes(mode);

    if (urlModeIsValid) {
      newMode = urlMode;
    } else if (modeStateIsValid) {
      newMode = mode;
    } else {
      newMode = supportedModes[0];
    }
  } else {
    newMode = [ExploreMode.Metrics, ExploreMode.Logs].includes(urlMode) ? urlMode : ExploreMode.Metrics;
  }

  const initialUI = ui || DEFAULT_UI_STATE;

  return {
    StartPage,
    datasourceError,
    datasourceInstance,
    datasourceLoading,
    datasourceMissing,
    initialized,
    showingStartPage,
    split,
    queryKeys,
    update,
    initialDatasource,
    initialQueries,
    initialRange,
    mode: newMode,
    initialUI,
    queryErrors,
    isLive,
  };
}

const mapDispatchToProps = {
  changeSize,
  initializeExplore,
  modifyQueries,
  reconnectDatasource,
  refreshExplore,
  scanStart,
  scanStopAction,
  setQueries,
  updateTimeRange,
};

export default hot(module)(
  connect(
    mapStateToProps,
    mapDispatchToProps
  )(Explore)
) as React.ComponentType<{ exploreId: ExploreId }>;
