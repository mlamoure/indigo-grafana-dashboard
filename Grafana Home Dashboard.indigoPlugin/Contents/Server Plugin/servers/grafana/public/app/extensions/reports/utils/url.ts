import { Report } from '../../types';

import { collectVariables } from './variables';

export const getUrlValues = () => {
  if (!window.location.search) {
    return null;
  }

  const urlParams = new URLSearchParams(window.location.search);
  return {
    timeRange: {
      to: urlParams.get('to') || '',
      from: urlParams.get('from') || '',
    },
    dashboard: {
      uid: urlParams.get('db-uid'),
      id: urlParams.get('db-id'),
      name: urlParams.get('db-name'),
    },
    variables: collectVariables(),
  };
};

/**
 * Apply values from URL params as form's default, in case a report is created
 * from dashboard
 * @param report
 */
export const applyUrlValues = (report: Report) => {
  // Do not apply URL values for edited report
  if (report.id) {
    return report;
  }
  const values = getUrlValues();
  if (!values) {
    return report;
  }

  const { timeRange, dashboard, variables } = values;

  if (timeRange?.from && timeRange?.to) {
    report = {
      ...report,
      options: {
        ...report.options,
        timeRange,
      },
    };
  }

  if (dashboard.name && dashboard.id && dashboard.uid) {
    report = {
      ...report,
      dashboardName: dashboard.name,
      dashboardId: Number(dashboard.id),
      dashboardUid: dashboard.uid,
    };
  }

  if (variables && Object.keys(variables).length) {
    report.templateVars = variables;
  }
  return report;
};
