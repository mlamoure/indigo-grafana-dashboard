import { css } from '@emotion/css';
import React, { useEffect, useState } from 'react';
import { UnpackNestedValue } from 'react-hook-form';
import { connect, ConnectedProps } from 'react-redux';

import { AppEvents, DataSourceInstanceSettings, GrafanaTheme2 } from '@grafana/data';
import { DataSourcePicker, getDataSourceSrv } from '@grafana/runtime';
import { Button, Field, Form, Icon, Input, useStyles2 } from '@grafana/ui';
import appEvents from 'app/core/app_events';
import Page from 'app/core/components/Page/Page';
import { getNavModel } from 'app/core/selectors/navModel';

import { EnterpriseStoreState, PrometheusWriteTarget } from '../types';

import { getPrometheusWriteTarget, savePrometheusWriteTarget } from './state/actions';
import { getRecordedQueryWriter } from './state/selectors';

export type Props = ConnectedProps<typeof connector>;

function mapStateToProps(state: EnterpriseStoreState) {
  return {
    navModel: getNavModel(state.navIndex, 'recordedQueries'),
    prometheusWriteTarget: getRecordedQueryWriter(state.recordedQueries),
  };
}

const mapDispatchToProps = {
  getPrometheusWriteTarget,
};

const connector = connect(mapStateToProps, mapDispatchToProps);

export const WriteTargetConfigUnconnected = ({ navModel, prometheusWriteTarget, getPrometheusWriteTarget }: Props) => {
  const [selectedDataSource, setSelectedDataSource] = useState<DataSourceInstanceSettings | undefined>();
  const [writePath, setWritePath] = useState<string | undefined>(prometheusWriteTarget?.remote_write_path);
  const styles = useStyles2(getStyles);

  useEffect(getPrometheusWriteTarget, [getPrometheusWriteTarget]);
  useEffect(() => {
    const getWriteTarget = async () => {
      if (prometheusWriteTarget) {
        const selectedDataSource = await getDataSourceSrv().getInstanceSettings(prometheusWriteTarget.data_source_uid);
        setSelectedDataSource(selectedDataSource);
      }
    };
    getWriteTarget();
  }, [prometheusWriteTarget]);

  const onSubmit = (data: UnpackNestedValue<PrometheusWriteTarget>) => {
    updateWriteTarget(selectedDataSource?.uid!, data.remote_write_path);
  };

  const label = (
    <span>
      {'Select the data source where metrics will be written'}
      <a
        href="https://grafana.com/docs/grafana/latest/enterprise/recorded-queries/#remote-write-target"
        className={styles.docsLink}
        target="_blank"
        rel="noreferrer"
      >
        <Icon name="info-circle" />
      </a>
    </span>
  );

  return (
    <Page navModel={navModel}>
      <Page.Contents>
        <Form key={prometheusWriteTarget?.data_source_uid} defaultValues={prometheusWriteTarget} onSubmit={onSubmit}>
          {({ register }) => (
            <>
              <Field label={label}>
                <DataSourcePicker
                  onChange={setSelectedDataSource}
                  current={selectedDataSource?.name}
                  placeholder={'Select a data source'}
                  type={'prometheus'}
                  noDefault={true}
                  alerting={true}
                  aria-label="Write target config select data source"
                />
              </Field>
              <Field label="Remote write path">
                <Input
                  {...register('remote_write_path')}
                  onChange={(e) => setWritePath(e.currentTarget.value)}
                  placeholder="/api/v1/write"
                  aria-label="Write target config remote write path"
                />
              </Field>
              <Button
                disabled={Boolean(!writePath || !selectedDataSource)}
                type="submit"
                aria-label="Write target config save"
              >
                Save
              </Button>
            </>
          )}
        </Form>
      </Page.Contents>
    </Page>
  );
};

function updateWriteTarget(data_source_uid: string, remote_write_path?: string) {
  savePrometheusWriteTarget({
    data_source_uid,
    remote_write_path,
  } as PrometheusWriteTarget)
    .then(() => {
      appEvents.emit(AppEvents.alertSuccess, [`Prometheus remote write target created`]);
    })
    .catch((error) => {
      appEvents.emit(AppEvents.alertError, [error.data.message]);
    });
}

const getStyles = (theme: GrafanaTheme2) => {
  return {
    docsLink: css`
      margin-left: ${theme.spacing(1)};
    `,
  };
};

export const WriteTargetConfig = connector(WriteTargetConfigUnconnected);
