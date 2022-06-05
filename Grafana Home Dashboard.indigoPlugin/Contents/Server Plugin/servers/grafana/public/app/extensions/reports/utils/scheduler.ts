import { dateTime } from '@grafana/data';
import { formatUtcOffset } from '@grafana/ui/src/components/DateTimePickers/TimeZonePicker/TimeZoneOffset';

import { IntervalFrequency, ReportTime, SchedulingData, SchedulingFrequency, SchedulingOptions } from '../../types';
import { initialState } from '../state/reducers';

import { getTime, createDate, getDate, padTime } from './dateTime';

/**
 * Process schedule data
 * @param scheduleData
 */
export const getSchedule = (scheduleData = {} as SchedulingData) => {
  const {
    time,
    startDate,
    endDate,
    endTime,
    timeZone,
    frequency,
    dayOfMonth,
    workdaysOnly,
    intervalFrequency,
    intervalAmount,
    sendTime,
  } = scheduleData;
  const parsedTime = !time && startDate ? getTime(String(startDate)) : time;
  const combinedStartDate =
    startDate && sendTime !== 'now' ? createDate(startDate, parsedTime as ReportTime, timeZone) : '';
  const combinedEndDate =
    endDate && ![SchedulingFrequency.Once, SchedulingFrequency.Never].includes(frequency)
      ? createDate(endDate, endTime as unknown as ReportTime, timeZone)
      : '';
  const options = {
    frequency,
    timeZone,
    workdaysOnly,
    intervalFrequency,
    intervalAmount: intervalAmount ? parseInt(intervalAmount, 10) : 0,
    startDate: combinedStartDate,
    endDate: combinedEndDate,
    dayOfMonth: dayOfMonth ? 'last' : '',
  };

  // Remove empty/falsy fields from the schedule object
  return Object.fromEntries(Object.entries(options).filter(([_, val]) => val)) as unknown as SchedulingOptions;
};

export function getOrdinal(n: number) {
  const suffixes = ['th', 'st', 'nd', 'rd'];
  const value = n % 100;
  return n + (suffixes[(value - 20) % 10] || suffixes[value] || suffixes[0]);
}

export const isHourFrequency = (frequency: SchedulingFrequency, interval = IntervalFrequency.Hours) => {
  return frequency === SchedulingFrequency.Custom && interval === IntervalFrequency.Hours;
};

export const showWorkdaysOnly = (frequency: SchedulingFrequency, interval = IntervalFrequency.Hours) => {
  return (
    [SchedulingFrequency.Hourly, SchedulingFrequency.Daily].includes(frequency) || isHourFrequency(frequency, interval)
  );
};

export function parseScheduleTime({
  startDate,
  endDate,
  intervalFrequency = IntervalFrequency.Hours,
  intervalAmount = 2,
  frequency,
  dayOfMonth,
  timeZone,
  workdaysOnly,
}: SchedulingOptions) {
  if (!startDate) {
    return '';
  }

  const locale = 'en-US';
  const { hour: h, minute: m } = getTime(startDate);
  const minute = padTime(m);
  const hour = padTime(h);
  const day = dateTime(getDate(startDate)).locale(locale).format('dddd');
  const date = dayOfMonth === 'last' ? `the last` : getOrdinal((getDate(startDate) as Date).getDate());
  let duration, time;
  const offset = formatUtcOffset(Date.now(), timeZone);
  const timeString = `at ${hour}:${minute}${offset ? ` ${offset}` : ''}`;
  const workdaysOnlyStr = workdaysOnly && showWorkdaysOnly(frequency, intervalFrequency) ? ', Monday to Friday' : '';
  if (endDate) {
    duration = `${dateTime(getDate(startDate)).locale(locale).format('LL')} - ${dateTime(getDate(endDate))
      .locale(locale)
      .format('LL')}`;
  }

  switch (frequency) {
    case SchedulingFrequency.Monthly:
      time = `Monthly on ${date} day ${timeString}`;
      break;
    case SchedulingFrequency.Weekly:
      time = `Every ${day} ${timeString}`;
      break;
    case SchedulingFrequency.Daily:
      time = `Daily ${timeString}`;
      break;
    case SchedulingFrequency.Hourly:
      time = `Hourly at minute ${minute}`;
      break;
    case SchedulingFrequency.Custom:
      time = `Every ${intervalAmount} ${intervalFrequency}`;
      break;
    case SchedulingFrequency.Once:
      time = `Once on ${dateTime(getDate(startDate)).locale(locale).format('LL')}`;
      break;
    case SchedulingFrequency.Never:
      time = `Never`;
      break;
  }

  if (duration && time) {
    return `${time}, ${duration}${workdaysOnlyStr}`;
  } else if (frequency === SchedulingFrequency.Custom) {
    time += `, ${
      intervalFrequency === IntervalFrequency.Hours
        ? `from ${hour}:${minute}${offset ? ` ${offset}` : ''}`
        : `from ${dateTime(getDate(startDate)).locale(locale).format('LL')}`
    }`;
  }

  return time + workdaysOnlyStr;
}

const recurrenceMap = new Map([
  [SchedulingFrequency.Monthly, 'month'],
  [SchedulingFrequency.Daily, 'day'],
  [SchedulingFrequency.Weekly, 'week'],
  [SchedulingFrequency.Hourly, 'hour'],
]);

export const schedulePreview = (schedule: SchedulingData) => {
  const { frequency, intervalFrequency = IntervalFrequency.Hours, intervalAmount = '2' } = schedule;
  if (frequency === SchedulingFrequency.Never) {
    return 'The report will not be sent.';
  }

  const workdaysOnly = schedule.workdaysOnly ? ', Monday to Friday.' : '.';
  if (!schedule.sendTime || schedule.sendTime === 'now') {
    let preview = `The report will be sent immediately after it is saved`;
    let recurrence;
    if (recurrenceMap.has(frequency)) {
      recurrence = recurrenceMap.get(frequency);
    } else if (frequency === SchedulingFrequency.Custom) {
      recurrence = `${intervalAmount}  ${intervalFrequency}`;
    }
    if (recurrence) {
      preview += ` and will be sent every ${recurrence}`;
    }

    return `${preview}${workdaysOnly}`;
  }
  const preview = parseScheduleTime(getSchedule(schedule));

  if (preview) {
    return `The report will be sent: ${preview}.`;
  }

  return '';
};

export const scheduleUpdated = (newSchedule: Partial<SchedulingOptions>) => {
  const originalSchedule = initialState.report.schedule;

  if (Object.keys(originalSchedule).length !== Object.keys(newSchedule).length) {
    return true;
  }

  return Object.entries(originalSchedule).some(([key, value]) => value !== newSchedule[key as keyof SchedulingOptions]);
};
