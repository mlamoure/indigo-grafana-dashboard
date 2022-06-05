import { cx } from '@emotion/css';
import React, { PureComponent } from 'react';

import { ArrayVector, DataFrame, dateTime, FieldType, TimeRange } from '@grafana/data';
import { LegendDisplayMode, TooltipDisplayMode } from '@grafana/schema';
import { Graph, Themeable2, VizTooltip } from '@grafana/ui';

import { SeriesOptions } from '../../types/flotgraph';
import { getGraphSeriesModel } from '../GraphSeriesModel';
import { DAILY_SUMMARY_DATE_FORMAT, DashboardDailySummaryDTO } from '../api';
import { getInsightsStyles } from '../styles';

interface Props extends Themeable2 {
  dailySummaries: DashboardDailySummaryDTO[];
}

interface ChartConfig {
  title: string;
  valueField: keyof DashboardDailySummaryDTO;
  fieldType: FieldType;
  width: number;
  timeRange: TimeRange;
  color: string;
  showBars: boolean;
  showLines: boolean;
}

// AnalyticsTab is a class made to share functions between the different Tabs of the Analytics Drawer
export class AnalyticsTab<T extends Props, V = any> extends PureComponent<T, V> {
  convertSummariesToDataFrame(
    data: DashboardDailySummaryDTO[],
    valueField: keyof DashboardDailySummaryDTO,
    valueFieldType: FieldType
  ): DataFrame {
    const time = new ArrayVector<number>([]);
    const values = new ArrayVector<any>([]);

    data.forEach((dailySummary) => {
      time.buffer.push(dateTime(dailySummary.day, DAILY_SUMMARY_DATE_FORMAT).valueOf());
      values.buffer.push(dailySummary[valueField]);
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

  buildTimeRange(): TimeRange {
    const { dailySummaries } = this.props;
    const from = dateTime(dailySummaries[0].day);
    const to = dateTime(dailySummaries[dailySummaries.length - 1].day).add(12, 'hours');

    return {
      from: from,
      to: to,
      raw: { from, to },
    };
  }

  renderChart(config: ChartConfig) {
    const { dailySummaries, theme } = this.props;
    const { color, fieldType, showBars, showLines, timeRange, title, valueField, width } = config;

    const styles = getInsightsStyles(theme);

    const dataFrame = this.convertSummariesToDataFrame(dailySummaries, valueField, fieldType);

    const seriesOptions: SeriesOptions = {};
    seriesOptions[valueField] = { color: color };
    const series = getGraphSeriesModel(
      [dataFrame],
      'browser',
      seriesOptions,
      { showBars: showBars, showLines: showLines, showPoints: false },
      { placement: 'bottom', displayMode: LegendDisplayMode.Hidden }
    );

    return (
      <div className={cx(styles.graphContainer, 'panel-container')} aria-label="Graph container">
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
}
