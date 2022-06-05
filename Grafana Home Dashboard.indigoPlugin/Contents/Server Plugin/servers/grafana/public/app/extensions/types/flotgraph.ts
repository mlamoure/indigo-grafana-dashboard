import { YAxis } from '@grafana/data';
import { LegendDisplayMode, LegendPlacement, SortOrder, TooltipDisplayMode, VizTooltipOptions } from '@grafana/schema';

export interface SeriesOptions {
  color?: string;
  yAxis?: YAxis;
  [key: string]: any;
}
export interface GraphOptions {
  showBars: boolean;
  showLines: boolean;
  showPoints: boolean;
}

export interface Options {
  graph: GraphOptions;
  legend: {
    displayMode: LegendDisplayMode;
    placement: LegendPlacement;
  };
  series: {
    [alias: string]: SeriesOptions;
  };
  tooltipOptions: VizTooltipOptions;
}

export const defaults: Options = {
  graph: {
    showBars: false,
    showLines: true,
    showPoints: false,
  },
  legend: {
    displayMode: LegendDisplayMode.List,
    placement: 'bottom',
  },
  series: {},
  tooltipOptions: { mode: TooltipDisplayMode.Single, sort: SortOrder.Descending },
};

export interface GraphLegendEditorLegendOptions {
  displayMode: LegendDisplayMode;
  placement: LegendPlacement;
  stats?: string[];
  decimals?: number;
  sortBy?: string;
  sortDesc?: boolean;
}
