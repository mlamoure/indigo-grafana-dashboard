import { dateTime } from '@grafana/data';
import { getBackendSrv } from '@grafana/runtime';

export const DAILY_SUMMARY_DATE_FORMAT = 'YYYY-MM-DD';

export interface RecentUser {
  id: number;
  name?: string;
  avatarUrl: string;
  login: string;
  email?: string;
  hasCustomAvatar?: boolean;
}

export interface UserViewDTO {
  user: RecentUser;
  viewed: string;
}

export interface DashboardUsersInfoDTO {
  creator?: UserViewDTO;
  lastEditor?: UserViewDTO;
}

export interface DashboardDailySummaryDTO {
  day: string;
  dashboardId: number;
  views: number;
  queries: number;
  errors: number;
  loadDuration: number;
}

export interface DataSourceDailySummaryDTO {
  day: string;
  dataSourceId: number;
  views: number;
  queries: number;
  errors: number;
  loadDuration: number;
}

export const getRecentUsers = async (dashboardId: number): Promise<UserViewDTO[]> => {
  return await getBackendSrv().get(`/api/usage/dashboard/${dashboardId}/views/recent`);
};

export const getUserViews = async (dashboardId: number, limit: number): Promise<UserViewDTO[]> => {
  return await getBackendSrv().get(`/api/usage/dashboard/${dashboardId}/views?limit=${limit}`);
};

const formatSummaries = <T extends DashboardDailySummaryDTO | DataSourceDailySummaryDTO>(apiSummaries: any): T[] => {
  const summariesArray: T[] = [];
  for (let day in apiSummaries) {
    summariesArray.push(apiSummaries[day]);
  }
  summariesArray.sort(
    (a, b) =>
      dateTime(a.day, DAILY_SUMMARY_DATE_FORMAT).valueOf() - dateTime(b.day, DAILY_SUMMARY_DATE_FORMAT).valueOf()
  );

  return summariesArray;
};

export const getDashboardDailySummaries = async (
  dashboardId: number,
  days: string[]
): Promise<DashboardDailySummaryDTO[]> => {
  const dailySummaries = await getBackendSrv().get(`/api/usage/dashboard/${dashboardId}/daily`, {
    days,
  });
  return formatSummaries<DashboardDailySummaryDTO>(dailySummaries);
};

export const getDataSourceDailySummaries = async (
  dataSourceUid: string,
  from: string,
  to: string
): Promise<DataSourceDailySummaryDTO[]> => {
  const dailySummaries = await getBackendSrv().get(`/api/usage/datasource/${dataSourceUid}/daily`, {
    from,
    to,
  });
  return formatSummaries<DataSourceDailySummaryDTO>(dailySummaries);
};

export const getDashboardUsersInfo = async (dashboardId: number): Promise<DashboardUsersInfoDTO> => {
  return await getBackendSrv().get(`/api/usage/dashboard/${dashboardId}/info`);
};
