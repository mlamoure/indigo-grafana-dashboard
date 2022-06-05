import { css } from '@emotion/css';
import React from 'react';
import { useForm } from 'react-hook-form';
import { connect, ConnectedProps } from 'react-redux';

import { GrafanaTheme2 } from '@grafana/data';
import { featureEnabled } from '@grafana/runtime';
import {
  Alert,
  Button,
  Checkbox,
  Field,
  FieldSet,
  Input,
  InputControl,
  ModalsController,
  TagsInput,
  TextArea,
  useStyles2,
} from '@grafana/ui';
import { contextSrv } from 'app/core/core';
import { GrafanaRouteComponentProps } from 'app/core/navigation/types';

import { AccessControlAction, EnterpriseStoreState, ReportFormData, StepKey } from '../../types';
import { emailSeparator, isEmail, validateMultipleEmails } from '../../utils/validators';
import { SendTestEmailModal } from '../SendTestEmailModal';
import { sendTestEmail } from '../state/actions';
import { updateReportProp } from '../state/reducers';
import { canEditReport } from '../utils/permissions';

import ReportForm from './ReportForm';

type EmailData = Pick<ReportFormData, 'name' | 'replyTo' | 'recipients' | 'message' | 'enableDashboardUrl'>;

interface OwnProps extends GrafanaRouteComponentProps<{ id: string }> {}

const mapStateToProps = (state: EnterpriseStoreState) => {
  const { testEmailIsSending, report } = state.reports;
  return {
    report,
    testEmailIsSending,
  };
};

const mapActionsToProps = {
  updateReportProp,
  sendTestEmail,
};

const connector = connect(mapStateToProps, mapActionsToProps);
export type Props = ConnectedProps<typeof connector> & OwnProps;

export const Share = ({ report, updateReportProp, sendTestEmail, testEmailIsSending }: Props) => {
  const { message, name, recipients, replyTo, enableDashboardUrl, dashboardId } = report;
  const {
    handleSubmit,
    control,
    register,
    setError,
    clearErrors,
    watch,
    getValues,
    formState: { errors, isDirty },
  } = useForm();
  const styles = useStyles2(getStyles);
  const canSendEmail = contextSrv.hasPermission(AccessControlAction.ReportingSend);
  const watchName = watch('name', name);
  const watchRecipients = watch('recipients', recipients);
  const disabled = !featureEnabled('reports.email') || !dashboardId;
  const sendEmailDisabled = !canSendEmail || disabled || !watchName || !watchRecipients;

  const onSendTestEmail = (email: string, useEmailsFromReport: boolean) => {
    const reportData = { ...report, ...getValues() };
    const recipients = useEmailsFromReport ? reportData.recipients : email;
    return sendTestEmail({ ...reportData, recipients });
  };

  const saveData = (data: EmailData) => {
    if (isDirty) {
      const { name } = data;
      updateReportProp({ ...report, ...data, name: name.trim() });
    }
  };

  return (
    <ReportForm activeStep={StepKey.Share} onSubmit={handleSubmit(saveData)} confirmRedirect={isDirty}>
      {testEmailIsSending && (
        <div className={'page-alert-list'}>
          <Alert title={'Sending test email...'} severity={'info'} elevated />
        </div>
      )}
      <FieldSet label={'4. Share'} disabled={!canEditReport}>
        <Field label="Report name" required invalid={!!errors.name} error="Name is required">
          <Input {...register('name')} type="text" id="name" defaultValue={name} placeholder="System status report" />
        </Field>
        <Field
          className={styles.field}
          label="Recipients"
          required
          invalid={!!errors.recipients}
          error={errors.recipients?.message}
          description={'Separate multiple emails with a comma or semicolon.'}
        >
          <InputControl
            name="recipients"
            control={control}
            defaultValue={recipients}
            render={({ field: { ref, value, onChange, ...field } }) => {
              return (
                <TagsInput
                  {...field}
                  disabled={!canEditReport}
                  invalid={!!errors.recipients}
                  onChange={(tags) => {
                    const splitTags = tags
                      .join(';')
                      .split(emailSeparator)
                      .filter(Boolean)
                      .map((tag) => tag.trim());
                    const invalidEmails = splitTags.filter((tag) => !isEmail(tag));
                    if (invalidEmails.length) {
                      setError('recipients', {
                        type: 'manual',
                        message: `Invalid email${invalidEmails.length > 1 ? 's' : ''}: ${invalidEmails.join('; ')}`,
                      });
                    } else {
                      clearErrors('recipients');
                    }
                    onChange(splitTags.filter((tag) => isEmail(tag)).join(';'));
                  }}
                  placeholder={'Type in the recipients email addresses and press Enter'}
                  tags={value ? value.split(emailSeparator) : []}
                  className={styles.tagsInput}
                  addOnBlur
                />
              );
            }}
            rules={{
              validate: (val) => {
                return validateMultipleEmails(val) || 'Invalid email';
              },
            }}
          />
        </Field>
        <Field
          className={styles.field}
          label="Reply-to email address"
          description={'The address that will appear in the Reply to field of the email'}
        >
          <Input
            {...register('replyTo')}
            id="replyTo"
            placeholder="your.address@company.com - optional"
            type="email"
            defaultValue={replyTo}
          />
        </Field>
        <Field className={styles.field} label="Message">
          <TextArea {...register('message')} id="message" placeholder={message} rows={10} defaultValue={message} />
        </Field>
        <Field className={styles.field}>
          <Checkbox
            {...register('enableDashboardUrl')}
            defaultChecked={enableDashboardUrl}
            label="Include a dashboard link"
          />
        </Field>

        <ModalsController>
          {({ showModal, hideModal }) => (
            <Button
              disabled={sendEmailDisabled}
              size="xs"
              variant="secondary"
              onClick={(e) => {
                e.preventDefault();
                showModal(SendTestEmailModal, {
                  onDismiss: hideModal,
                  onSendTestEmail,
                  emails: watchRecipients,
                });
              }}
            >
              Send test email
            </Button>
          )}
        </ModalsController>
      </FieldSet>
    </ReportForm>
  );
};

const getStyles = (theme: GrafanaTheme2) => {
  return {
    field: css`
      &:not(:last-of-type) {
        margin-bottom: ${theme.spacing(3)};
      }
    `,
    tagsInput: css`
      & > div:first-of-type {
        margin-bottom: ${theme.spacing(1)};
        div {
          background-color: ${theme.colors.background.secondary};
          border-color: ${theme.components.input.borderColor};
          color: ${theme.colors.text.primary};

          & > span {
            color: ${theme.colors.text.primary};
          }
        }
      }

      & > div:not(:first-of-type) {
        width: 100%;
      }
    `,
  };
};
export default connector(Share);
