export enum AnalyticsTab {
  Stats = 'stats',
  Users = 'users',
}

export interface MetaAnalyticsState {
  isDrawerOpen: boolean;
  drawerTab: AnalyticsTab;
}
