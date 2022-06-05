import { createSlice, PayloadAction } from '@reduxjs/toolkit';

import { dateTime, TimeRange } from '@grafana/data';
import { toStateKey } from 'app/features/variables/utils';

import { FooterMode, Report, ReportsState, ReportTimeRange, SchedulingFrequency, StepKey } from '../../types';

export const getTimezone = () => {
  // Older browser does not the internationalization API
  if (!(window as any).Intl) {
    return '';
  }

  const dateFormat = (window as any).Intl.DateTimeFormat();
  if (!dateFormat.resolvedOptions) {
    return '';
  }

  const options = dateFormat.resolvedOptions();
  if (!options.timeZone) {
    return '';
  }

  return options.timeZone;
};

export const defaultTimeRange: TimeRange = {
  from: dateTime(null),
  to: dateTime(null),
  raw: { from: '', to: '' },
};

const blankReport: Report = {
  id: 0,
  name: '',
  recipients: '',
  replyTo: '',
  message: 'Hi, \nPlease find attached a PDF status report. If you have any questions, feel free to contact me!\nBest,',
  dashboardId: undefined,
  dashboardName: '',
  schedule: {
    frequency: SchedulingFrequency.Weekly,
    timeZone: getTimezone(),
  },
  options: {
    orientation: 'landscape',
    layout: 'grid',
    timeRange: defaultTimeRange.raw as ReportTimeRange,
  },
  enableDashboardUrl: true,
  enableCsv: false,
};

export const initialState: ReportsState = {
  reports: [] as Report[],
  report: blankReport,
  hasFetchedList: false,
  hasFetchedSingle: false,
  searchQuery: '',
  reportCount: 0,
  isLoading: true,
  isUpdated: false,
  visitedSteps: [],
  settings: {
    branding: {
      reportLogoUrl: '',
      emailLogoUrl: '',
      emailFooterMode: FooterMode.SentBy,
      emailFooterText: '',
      emailFooterLink: '',
    },
  },
};

const reportsSlice = createSlice({
  name: 'reports',
  initialState,
  reducers: {
    reportsLoaded: (state: ReportsState, action: PayloadAction<Report[]>): ReportsState => ({
      ...state,
      reports: action.payload,
      reportCount: action.payload.length,
      hasFetchedList: true,
    }),
    reportLoaded: (state: ReportsState, action: PayloadAction<Report>): ReportsState => ({
      ...state,
      report: action.payload,
      hasFetchedSingle: true,
      isLoading: false,
    }),
    updateReportProp: (state: ReportsState, action: PayloadAction<Report>): ReportsState => ({
      ...state,
      isUpdated: true,
      report: action.payload,
    }),
    clearReportState: (state: ReportsState): ReportsState => ({
      ...state,
      isUpdated: false,
      visitedSteps: [],
      report: blankReport,
    }),
    reportLoadingBegin: (state: ReportsState) => ({
      ...state,
      isLoading: true,
    }),
    reportLoadingEnd: (state: ReportsState) => ({
      ...state,
      isLoading: false,
    }),
    testEmailSendBegin: (state: ReportsState) => ({
      ...state,
      testEmailIsSending: true,
    }),
    testEmailSendEnd: (state: ReportsState) => ({
      ...state,
      testEmailIsSending: false,
    }),
    setLastUid: (state: ReportsState, action: PayloadAction<string | undefined>): ReportsState => ({
      ...state,
      lastUid: toStateKey(action.payload),
    }),
    addVisitedStep: (state: ReportsState, action: PayloadAction<StepKey[]>) => {
      return { ...state, visitedSteps: [...state.visitedSteps, ...action.payload] };
    },
  },
});

export const {
  clearReportState,
  reportLoaded,
  reportsLoaded,
  updateReportProp,
  reportLoadingBegin,
  reportLoadingEnd,
  testEmailSendBegin,
  testEmailSendEnd,
  setLastUid,
  addVisitedStep,
} = reportsSlice.actions;

export const reportsReducers = reportsSlice.reducer;

export default {
  reports: reportsReducers,
};
