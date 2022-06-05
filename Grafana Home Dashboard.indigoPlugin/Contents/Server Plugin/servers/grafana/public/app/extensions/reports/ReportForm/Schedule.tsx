import { css } from '@emotion/css';
import React from 'react';
import { useForm } from 'react-hook-form';
import { connect, ConnectedProps } from 'react-redux';

import { dateTime, GrafanaTheme2, SelectableValue } from '@grafana/data';
import {
  Checkbox,
  DatePickerWithInput,
  Field,
  FieldSet,
  HorizontalGroup,
  Icon,
  Input,
  InputControl,
  RadioButtonGroup,
  Select,
  TimeOfDayPicker,
  TimeZonePicker,
  useStyles2,
} from '@grafana/ui';
import { GrafanaRouteComponentProps } from 'app/core/navigation/types';

import { EnterpriseStoreState, IntervalFrequency, ReportFormData, SchedulingFrequency, StepKey } from '../../types';
import { getTimezone, updateReportProp } from '../state/reducers';
import { getDate, getTime } from '../utils/dateTime';
import { canEditReport } from '../utils/permissions';
import { isHourFrequency, schedulePreview, showWorkdaysOnly, getOrdinal, getSchedule } from '../utils/scheduler';

import ReportForm from './ReportForm';

interface OwnProps extends GrafanaRouteComponentProps<{ id: string }> {}

const mapStateToProps = (state: EnterpriseStoreState) => {
  return {
    report: state.reports.report,
  };
};

const mapActionsToProps = {
  updateReportProp,
};

const connector = connect(mapStateToProps, mapActionsToProps);
export type Props = ConnectedProps<typeof connector> & OwnProps;

const frequencyOptions: SelectableValue[] = [
  { label: 'Once', value: SchedulingFrequency.Once },
  { label: 'Hourly', value: SchedulingFrequency.Hourly },
  { label: 'Daily', value: SchedulingFrequency.Daily },
  { label: 'Weekly', value: SchedulingFrequency.Weekly },
  { label: 'Monthly', value: SchedulingFrequency.Monthly },
  { label: 'Custom', value: SchedulingFrequency.Custom },
  { label: 'Never', value: SchedulingFrequency.Never },
];

const intervalOptions: SelectableValue[] = [
  { label: 'hours', value: IntervalFrequency.Hours },
  { label: 'days', value: IntervalFrequency.Days },
  { label: 'weeks', value: IntervalFrequency.Weeks },
  { label: 'months', value: IntervalFrequency.Months },
];

const sendOnTheLastDay = (sendTime: string) =>
  sendTime === 'now' && [29, 30, 31].includes(dateTime().toDate().getDate());

export const Schedule = ({ report, updateReportProp }: Props) => {
  const {
    handleSubmit,
    control,
    watch,
    register,
    setValue,
    formState: { isDirty },
  } = useForm();
  const { frequency, timeZone, startDate, endDate, dayOfMonth, intervalAmount, intervalFrequency } = report.schedule;
  const defaultStartDate = frequency === SchedulingFrequency.Never ? '' : startDate;
  const defaultSendTime = defaultStartDate ? 'later' : 'now';
  const defaultSchedule = {
    startDate: defaultStartDate,
    sendTime: defaultSendTime,
    intervalFrequency: IntervalFrequency.Hours,
    intervalAmount: '2',
  };

  const watchSchedule = watch('schedule', { ...defaultSchedule, ...report.schedule }) || {};
  const {
    frequency: watchFrequency,
    startDate: watchStartDate,
    endDate: watchEndDate,
    intervalFrequency: watchIntervalFrequency = IntervalFrequency.Hours,
    dayOfMonth: watchDayOfMonth,
    sendTime: watchSendTime = defaultSendTime,
    workdaysOnly: watchWorkdaysOnly,
  } = watchSchedule;
  const styles = useStyles2(getStyles);
  const date = new Date(watchStartDate).getDate();

  const saveData = (data: Partial<ReportFormData>) => {
    if (isDirty) {
      const schedule = getSchedule(data.schedule);
      updateReportProp({ ...report, schedule });
    }
  };

  return (
    <ReportForm activeStep={StepKey.Schedule} onSubmit={handleSubmit(saveData)} confirmRedirect={isDirty}>
      <FieldSet label="3. Schedule">
        <Field label="Frequency">
          <InputControl
            defaultValue={frequency}
            name="schedule.frequency"
            render={({ field: { ref, onChange, ...field } }) => (
              <RadioButtonGroup
                {...field}
                fullWidth
                options={frequencyOptions}
                disabled={!canEditReport}
                onChange={(val) => {
                  if (!showWorkdaysOnly(val, watchIntervalFrequency)) {
                    setValue('schedule.workdaysOnly', false);
                  }
                  onChange(val);
                }}
              />
            )}
            control={control}
          />
        </Field>

        {watchFrequency !== SchedulingFrequency.Never && (
          <Field label={'Time'}>
            <InputControl
              control={control}
              name={'schedule.sendTime'}
              defaultValue={defaultSendTime}
              render={({ field: { ref, onChange, ...field } }) => (
                <RadioButtonGroup
                  {...field}
                  onChange={(value) => {
                    if (value !== 'now' && !watchStartDate) {
                      setValue('schedule.startDate', dateTime().toDate());
                    } else if (value === 'now') {
                      setValue('schedule.startDate', '');
                    }
                    onChange(value);
                  }}
                  options={[
                    { label: 'Send now', value: 'now' },
                    { label: 'Send later', value: 'later' },
                  ]}
                />
              )}
            />
          </Field>
        )}

        <>
          {watchFrequency === SchedulingFrequency.Custom && (
            <HorizontalGroup>
              <Field label={'Repeat every'}>
                <Input
                  type={'number'}
                  min={'2'}
                  {...register('schedule.intervalAmount')}
                  placeholder={'e.g. 2'}
                  defaultValue={intervalAmount || 2}
                  id={'repeat-frequency'}
                />
              </Field>
              <Field label={' '}>
                <InputControl
                  control={control}
                  defaultValue={
                    intervalOptions.find((opt) => opt.value === intervalFrequency)?.value || IntervalFrequency.Hours
                  }
                  render={({ field: { ref, onChange, ...field } }) => (
                    <Select
                      {...field}
                      onChange={(interval) => onChange(interval.value)}
                      options={intervalOptions}
                      width={16}
                      placeholder={'hours'}
                      aria-label={'Custom frequency'}
                    />
                  )}
                  name={'schedule.intervalFrequency'}
                />
              </Field>
            </HorizontalGroup>
          )}

          {watchFrequency === SchedulingFrequency.Monthly &&
            (sendOnTheLastDay(watchSendTime) || watchSendTime === 'later') && (
              <Field>
                <InputControl
                  control={control}
                  defaultValue={dayOfMonth === 'last'}
                  render={({ field: { onChange, ...field } }) => (
                    <Checkbox
                      {...field}
                      label={'Send on the last day of month'}
                      onChange={(val) => {
                        setValue('schedule.startDate', dateTime().endOf('month').toDate());
                        onChange(val);
                      }}
                    />
                  )}
                  name={'schedule.dayOfMonth'}
                />
              </Field>
            )}
        </>

        {/*Hide date/time fields instead of completely removing them, so the timezone value doesn't get reset */}
        <div className={watchSendTime !== 'now' && watchFrequency !== SchedulingFrequency.Never ? '' : styles.hidden}>
          <HorizontalGroup width={'100%'}>
            <Field label={'Start date'}>
              <InputControl
                name={'schedule.startDate'}
                control={control}
                defaultValue={getDate(defaultStartDate)}
                render={({ field: { ref, ...field } }) => (
                  <DatePickerWithInput
                    {...field}
                    width={16}
                    placeholder={'Select date'}
                    aria-label={'Report schedule start date'}
                    closeOnSelect
                  />
                )}
              />
            </Field>

            <Field label="Start time">
              <InputControl
                name="schedule.time"
                render={({ field: { onChange, ref, value, ...field } }) => (
                  <TimeOfDayPicker
                    {...field}
                    value={value as any}
                    minuteStep={10}
                    disabled={!canEditReport}
                    onChange={(selected) => {
                      if (selected.isValid()) {
                        onChange({
                          hour: selected.hour?.(),
                          minute: selected.minute?.(),
                        });
                      }
                    }}
                  />
                )}
                defaultValue={getTime(startDate)}
                control={control}
              />
            </Field>
            <>
              <Field label="Time zone">
                <InputControl
                  name="schedule.timeZone"
                  render={({ field: { ref, ...field } }) => (
                    <TimeZonePicker {...field} width={30} disabled={!canEditReport} />
                  )}
                  defaultValue={timeZone || getTimezone()}
                  control={control}
                />
              </Field>
            </>
          </HorizontalGroup>
        </div>
        {watchFrequency === SchedulingFrequency.Monthly &&
          !watchDayOfMonth &&
          ([29, 30, 31].includes(date) || sendOnTheLastDay(watchSendTime)) && (
            <small className={styles.warningText}>
              Note: some months do not have a{' '}
              {getOrdinal(sendOnTheLastDay(watchSendTime) ? dateTime().toDate().getDate() : date)} day and reports will
              not be sent on those months. Choose an earlier date or{' '}
              <strong>&quot;Send on the last day of month&quot;</strong> to send a report at the end of each month.
            </small>
          )}
        {![SchedulingFrequency.Once, SchedulingFrequency.Never].includes(watchFrequency) && (
          <HorizontalGroup width={'100%'}>
            <Field label={'End date'}>
              <InputControl
                name={'schedule.endDate'}
                control={control}
                defaultValue={getDate(endDate)}
                render={({ field: { ref, ...field } }) => (
                  <DatePickerWithInput
                    {...field}
                    width={16}
                    placeholder={'Does not end'}
                    aria-label={'Report schedule end date'}
                    closeOnSelect
                  />
                )}
              />
            </Field>

            {watchEndDate &&
              (watchFrequency === SchedulingFrequency.Hourly ||
                isHourFrequency(watchFrequency, watchIntervalFrequency)) && (
                <Field label="End time">
                  <InputControl
                    name="schedule.endTime"
                    render={({ field: { onChange, ref, value, ...field } }) => (
                      <TimeOfDayPicker
                        {...field}
                        // The component is missing MomentInput type, even though moment.js is used for conversion
                        value={value as any}
                        minuteStep={10}
                        disabled={!canEditReport}
                        onChange={(selected) => {
                          if (selected?.isValid()) {
                            onChange({
                              hour: selected.hour?.(),
                              minute: selected.minute?.(),
                            });
                          }
                        }}
                      />
                    )}
                    defaultValue={getTime(endDate)}
                    control={control}
                  />
                </Field>
              )}
          </HorizontalGroup>
        )}

        {showWorkdaysOnly(watchFrequency, watchIntervalFrequency) && (
          <Field>
            <Checkbox
              {...register('schedule.workdaysOnly')}
              label={'Send Monday to Friday only'}
              defaultChecked={watchWorkdaysOnly}
            />
          </Field>
        )}
        <div className={styles.schedulePreview}>
          <Icon name={'calendar-alt'} />
          {schedulePreview({ ...defaultSchedule, ...watchSchedule })}
        </div>
      </FieldSet>
    </ReportForm>
  );
};

export default connector(Schedule);

const getStyles = (theme: GrafanaTheme2) => {
  return {
    warningText: css`
      color: ${theme.colors.warning.main};
      display: block;
      margin: -${theme.spacing(1)} 0 ${theme.spacing(3)} 0;
    `,
    hidden: css`
      display: none;
    `,
    schedulePreview: css`
      display: flex;
      align-items: center;

      svg {
        margin-right: ${theme.spacing(1)};
      }
    `,
  };
};
