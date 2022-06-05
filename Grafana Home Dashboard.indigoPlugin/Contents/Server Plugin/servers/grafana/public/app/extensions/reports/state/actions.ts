import { getBackendSrv } from '@grafana/runtime';
import { backendSrv } from 'app/core/services/backend_srv';
import { DashboardModel } from 'app/features/dashboard/state';
import { cleanUpVariables, initVariablesTransaction } from 'app/features/variables/state/actions';
import { ThunkResult } from 'app/types';

import { EnterpriseStoreState, Report, ReportDTO, SchedulingOptions } from '../../types';
import { applyDefaultVariables } from '../utils/variables';

import {
  reportLoaded,
  reportLoadingBegin,
  reportLoadingEnd,
  reportsLoaded,
  setLastUid,
  testEmailSendBegin,
  testEmailSendEnd,
} from './reducers';
import { getLastUid } from './selectors';

const baseUrl = 'api/reports';

export function getReports(): ThunkResult<void> {
  return async (dispatch) => {
    const reports = await getBackendSrv().get(baseUrl);
    dispatch(reportsLoaded(reports));
  };
}

export function initVariables(dashboardUid: string, templateVars?: Report['templateVars']): ThunkResult<void> {
  return async (dispatch, getState) => {
    const resp = await backendSrv.getDashboardByUid(dashboardUid);
    const dashboard = new DashboardModel(resp.dashboard, resp.meta);
    const list = applyDefaultVariables(dashboard.templating.list, templateVars);
    const state = getState() as EnterpriseStoreState;
    const lastUid = getLastUid(state);
    if (lastUid && lastUid !== dashboardUid) {
      dispatch(cleanUpVariables(lastUid));
    }
    dispatch(initVariablesTransaction(resp.dashboard.uid, { ...dashboard, templating: { list } } as DashboardModel));
    dispatch(setLastUid(dashboardUid));
  };
}

export function loadReport(id: number): ThunkResult<void> {
  return async (dispatch) => {
    dispatch(reportLoadingBegin());
    try {
      const report = await getBackendSrv().get(`${baseUrl}/${id}`);
      if (report?.dashboardUid) {
        dispatch(initVariables(report.dashboardUid, report.templateVars));
      }
      dispatch(reportLoaded(report));
    } catch (e) {
      dispatch(reportLoadingEnd());
    }
  };
}

export function sendTestEmail(report: ReportDTO): ThunkResult<void> {
  return (dispatch) => {
    dispatch(testEmailSendBegin());
    return getBackendSrv()
      .post(`${baseUrl}/test-email/`, report)
      .finally(() => dispatch(testEmailSendEnd()));
  };
}

export function deleteReport(id: number): ThunkResult<void> {
  return async (dispatch) => {
    await getBackendSrv().delete(`${baseUrl}/${id}`);
    dispatch(getReports());
  };
}

export function createReport(report: ReportDTO): ThunkResult<void> {
  return async (dispatch) => {
    try {
      await getBackendSrv().post(baseUrl, report);
    } catch (error) {
      throw error;
    }
    dispatch(getReports());
  };
}

export function updateReport(report: ReportDTO): ThunkResult<void> {
  return async (dispatch) => {
    const deprecatedFields = ['hour', 'minute', 'day'];
    report = {
      ...report,
      schedule: Object.fromEntries(
        Object.entries(report.schedule).filter(([key, _]: [string, any]) => !deprecatedFields.includes(key) as unknown)
      ) as SchedulingOptions,
    };
    await getBackendSrv().put(`${baseUrl}/${report.id}`, report);
    dispatch(getReports());
  };
}
