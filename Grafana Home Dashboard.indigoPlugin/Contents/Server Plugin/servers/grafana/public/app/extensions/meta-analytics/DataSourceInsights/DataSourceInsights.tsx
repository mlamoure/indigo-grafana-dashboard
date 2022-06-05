import { cx } from '@emotion/css';
import React, { PureComponent } from 'react';
import { connect, ConnectedProps } from 'react-redux';
import AutoSizer from 'react-virtualized-auto-sizer';

import { ArrayVector, DataFrame, dateTime, FieldType, TimeRange } from '@grafana/data';
import { featureEnabled } from '@grafana/runtime';
import { LegendDisplayMode, TooltipDisplayMode } from '@grafana/schema';
import { Graph, InfoBox, Themeable2, VizTooltip, withTheme2 } from '@grafana/ui';
import PageHeader from 'app/core/components/PageHeader/PageHeader';
import { UpgradeBox } from 'app/core/components/Upgrade/UpgradeBox';
import { GrafanaRouteComponentProps } from 'app/core/navigation/types';
import { getNavModel } from 'app/core/selectors/navModel';
import { highlightTrial } from 'app/features/admin/utils';
import { loadDataSource, loadDataSourceMeta } from 'app/features/datasources/state/actions';
import { getDataSourceLoadingNav } from 'app/features/datasources/state/navModel';

import { EnterpriseStoreState } from '../../types';
import { SeriesOptions } from '../../types/flotgraph';
import { getGraphSeriesModel } from '../GraphSeriesModel';
import { DAILY_SUMMARY_DATE_FORMAT, DataSourceDailySummaryDTO, getDataSourceDailySummaries } from '../api';
import { getInsightsStyles, InsightsStyles } from '../styles';

interface RouteProps extends GrafanaRouteComponentProps<{ uid: string }> {}

const mapStateToProps = (state: EnterpriseStoreState, props: RouteProps) => {
  const dataSourceUid = props.match.params.uid;
  const dataSourceLoadingNav = getDataSourceLoadingNav('insights');

  return {
    navModel: getNavModel(state.navIndex, `datasource-insights-${dataSourceUid}`, dataSourceLoadingNav),
    dataSourceUid,
  };
};

const mapDispatchToProps = {
  loadDataSource,
  loadDataSourceMeta,
};

export const connector = connect(mapStateToProps, mapDispatchToProps);

export type Props = Themeable2 & ConnectedProps<typeof connector>;

interface State {
  dailySummaries: DataSourceDailySummaryDTO[];
  from: string;
  to: string;
}

interface ChartConfig {
  title: string | JSX.Element;
  valueField: keyof DataSourceDailySummaryDTO;
  fieldType: FieldType;
  width: number;
  timeRange: TimeRange;
  color: string;
  showBars: boolean;
  showLines: boolean;
}

class DataSourceInsights extends PureComponent<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      dailySummaries: [],
      from: '',
      to: '',
    };
  }

  async componentDidMount(): Promise<void> {
    const { dataSourceUid, loadDataSource, loadDataSourceMeta } = this.props;

    loadDataSource(dataSourceUid).then(loadDataSourceMeta);

    if (featureEnabled('analytics')) {
      let from = dateTime().subtract(30, 'days').format(DAILY_SUMMARY_DATE_FORMAT);
      let to = dateTime().format(DAILY_SUMMARY_DATE_FORMAT);
      const dailySummaries = await getDataSourceDailySummaries(dataSourceUid, from, to);
      this.setState({ dailySummaries, from, to });
    }
  }

  buildTimeRange(): TimeRange {
    const { from, to } = this.state;

    const timeRangeFrom = dateTime(from);
    const timeRangeTo = dateTime(to).add(24, 'hours');

    return {
      from: timeRangeFrom,
      to: timeRangeTo,
      raw: { from, to },
    };
  }

  convertDailySummariesToDataFrame(
    data: DataSourceDailySummaryDTO[],
    valueField: keyof DataSourceDailySummaryDTO,
    valueFieldType: FieldType
  ): DataFrame {
    const time = new ArrayVector<number>([]);
    const values = new ArrayVector<any>([]);

    data.forEach((dailySummary) => {
      time.buffer.push(dateTime(dailySummary.day, DAILY_SUMMARY_DATE_FORMAT).valueOf());
      let value = dailySummary[valueField];
      if (valueField === 'loadDuration') {
        value = dailySummary.queries ? dailySummary.loadDuration / (dailySummary.queries * 1000000) : 0;
      }
      values.buffer.push(value);
    });

    return {
      name: valueField,
      fields: [
        { name: 'Time', type: FieldType.time, config: {}, values: time },
        { name: valueField, type: valueFieldType, config: {}, values: values },
      ],
      length: data.length,
    };
  }

  renderChart(config: ChartConfig, styles: InsightsStyles) {
    const { dailySummaries } = this.state;
    const { color, fieldType, showBars, showLines, timeRange, title, valueField, width } = config;

    let dataFrame = this.convertDailySummariesToDataFrame(dailySummaries, valueField, fieldType);

    const seriesOptions: SeriesOptions = { [valueField]: { color: color } };
    const series = getGraphSeriesModel(
      [dataFrame],
      'browser',
      seriesOptions,
      { showBars: showBars, showLines: showLines, showPoints: false },
      { placement: 'bottom', displayMode: LegendDisplayMode.Hidden }
    );

    return (
      <div
        className={cx(styles.graphContainer, 'panel-container')}
        aria-label="Graph container"
        key={config.valueField}
      >
        <div className="panel-title">{title}</div>
        <div className="panel-content">
          <Graph
            height={150}
            width={width}
            timeRange={timeRange}
            showBars={showBars}
            showLines={showLines}
            showPoints={false}
            series={series}
            timeZone="browser"
          >
            <VizTooltip mode={TooltipDisplayMode.Multi} />
          </Graph>
        </div>
      </div>
    );
  }

  renderContent() {
    const { theme } = this.props;
    const styles = getInsightsStyles(theme);
    const { dailySummaries } = this.state;
    const timeRange = this.buildTimeRange();

    return dailySummaries?.length > 0 ? (
      <AutoSizer disableHeight>
        {({ width }) => {
          const charts: ChartConfig[] = [
            {
              title: 'Queries last 30 days',
              valueField: 'queries',
              fieldType: FieldType.number,
              width,
              timeRange,
              color: '',
              showBars: true,
              showLines: false,
            },
            {
              title: 'Errors last 30 days',
              valueField: 'errors',
              fieldType: FieldType.number,
              width,
              timeRange,
              color: theme.colors.error.border,
              showBars: true,
              showLines: false,
            },
            {
              title: 'Average load duration last 30 days (ms)',
              valueField: 'loadDuration',
              fieldType: FieldType.number,
              width,
              timeRange,
              color: theme.colors.primary.border,
              showBars: true,
              showLines: false,
            },
          ];

          return <main style={{ width }}>{charts.map((chart) => this.renderChart(chart, styles))}</main>;
        }}
      </AutoSizer>
    ) : (
      <span>No available data for this data source.</span>
    );
  }

  render() {
    const { navModel } = this.props;

    return (
      <>
        <PageHeader model={navModel} />
        <div className="page-container page-body">
          {featureEnabled('analytics.writers') && !featureEnabled('analytics') ? (
            <InfoBox
              title="Feature not available with an expired license"
              url="https://grafana.com/docs/grafana/latest/enterprise/license-expiration/"
              urlTitle="Read more on license expiration"
            >
              <span>
                Data source insights are not available with an expired license. Data will continue to be collected but
                you need to update your license to see this page.
              </span>
            </InfoBox>
          ) : (
            <>
              {highlightTrial() && (
                <UpgradeBox
                  featureId={'data-source-insights'}
                  eventVariant={'trial'}
                  featureName={'data source usage insights'}
                  text={'Enable data source usage insights for free during your trial of Grafana Pro.'}
                />
              )}
              {this.renderContent()}
            </>
          )}
        </div>
      </>
    );
  }
}

export default connector(withTheme2(DataSourceInsights));
