import { Report, ReportDTO, ReportState, SchedulingFrequency } from '../../types';

import { isPast } from './dateTime';

export const getReportState = (report: ReportDTO) => {
  const { endDate, startDate, frequency } = report.schedule;

  if (frequency === SchedulingFrequency.Never) {
    return ReportState.Never;
  }
  if (isPast(endDate) || (frequency === SchedulingFrequency.Once && isPast(startDate))) {
    return ReportState.Expired;
  }

  return report.state || ReportState.Scheduled;
};

export const getReportStateInfo = (report: Report) => {
  const reportState = getReportState(report);
  const isNever = report.schedule.frequency === SchedulingFrequency.Never;
  const showPlay = isNever || [ReportState.Draft, ReportState.Expired, ReportState.Paused].includes(reportState);
  const disableEdit = isNever || [ReportState.Draft, ReportState.Expired].includes(reportState);

  return { isNever, showPlay, disableEdit, reportState };
};
