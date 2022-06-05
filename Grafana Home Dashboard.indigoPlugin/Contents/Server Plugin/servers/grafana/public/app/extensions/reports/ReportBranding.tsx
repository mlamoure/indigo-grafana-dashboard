import React, { FC } from 'react';

import { SelectableValue } from '@grafana/data';
import { Input, Field, FormAPI, RadioButtonGroup, FieldSet, InputControl } from '@grafana/ui';
import { contextSrv } from 'app/core/core';

import { AccessControlAction, FooterMode, ReportsSettings } from '../types';
import { isValidImageExt } from '../utils/validators';

import { ImagePreview } from './ImagePreview';
import { defaultEmailLogo, defaultReportLogo } from './constants';

interface Props extends FormAPI<ReportsSettings> {
  settings: ReportsSettings;
}

const footerModeOptions: SelectableValue[] = [
  { label: 'Sent By', value: FooterMode.SentBy },
  { label: 'None', value: FooterMode.None },
];

const validateImg = (val: string) => {
  return isValidImageExt(val) || 'Invalid image extension. Supported formats: png, jpg, gif.';
};

const ReportBranding: FC<Props> = ({ settings, register, control, watch, errors }) => {
  const { reportLogoUrl, emailLogoUrl, emailFooterMode, emailFooterText, emailFooterLink } = settings.branding;
  const watchReportLogo = watch('branding.reportLogoUrl', reportLogoUrl);
  const watchEmailLogo = watch('branding.emailLogoUrl', emailLogoUrl);
  const watchFooterMode = watch('branding.emailFooterMode', emailFooterMode || FooterMode.SentBy);
  const canEditSettings = contextSrv.hasPermission(AccessControlAction.ReportingSettingsWrite);

  return (
    <>
      <FieldSet label="Report branding" disabled={!canEditSettings}>
        <Field
          label="Company logo URL"
          description="The logo will be displayed in the document footer. Supported formats: png, jpg, gif."
          invalid={!!errors.branding?.reportLogoUrl}
          error={errors.branding?.reportLogoUrl?.message}
        >
          <Input
            {...register('branding.reportLogoUrl', {
              validate: validateImg,
            })}
            aria-label="Report logo"
            id="reportLogo"
            defaultValue={reportLogoUrl}
            placeholder="http://your.site/logo.png"
            type="url"
          />
        </Field>
        <ImagePreview url={(watchReportLogo || defaultReportLogo) as string} width="60px" />
      </FieldSet>

      <FieldSet label="Email branding" disabled={!canEditSettings}>
        <Field
          label="Company logo URL"
          description="The logo will be displayed in the email header. Supported formats: png, jpg, gif."
          invalid={!!errors.branding?.emailLogoUrl}
          error={errors.branding?.emailLogoUrl?.message}
        >
          <Input
            {...register('branding.emailLogoUrl', {
              validate: validateImg,
            })}
            aria-label="Email logo"
            id="emailLogo"
            defaultValue={emailLogoUrl}
            placeholder="http://your.site/logo.png"
            type="url"
          />
        </Field>
        <ImagePreview url={(watchEmailLogo || defaultEmailLogo) as string} />
        <Field label="Email footer">
          <InputControl
            defaultValue={emailFooterMode || FooterMode.SentBy}
            name="branding.emailFooterMode"
            render={({ field: { ref, ...field } }) => <RadioButtonGroup {...field} options={footerModeOptions} />}
            control={control}
          />
        </Field>
        {watchFooterMode === FooterMode.SentBy && (
          <>
            <Field label="Footer link text">
              <Input
                {...register('branding.emailFooterText')}
                id="emailFooterText"
                defaultValue={emailFooterText}
                placeholder="Grafana"
                type="text"
              />
            </Field>
            <Field label="Footer link URL">
              <Input
                {...register('branding.emailFooterLink')}
                id="emailFooterLink"
                defaultValue={emailFooterLink}
                placeholder="http://your.site"
                type="url"
              />
            </Field>
          </>
        )}
      </FieldSet>
    </>
  );
};

export default ReportBranding;
