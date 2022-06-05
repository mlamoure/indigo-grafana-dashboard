import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import { of } from 'rxjs';

import { DataSourceInstanceSettings, NavModel } from '@grafana/data';
import { DataSourcePickerProps } from '@grafana/runtime';

import { PrometheusWriteTarget } from '../types';

import { WriteTargetConfigUnconnected } from './WriteTargetConfig';

function MockPicker(props: DataSourcePickerProps) {
  return <></>;
}

const settingsMock = jest.fn().mockReturnValue({ uid: 'test-datasource-uid' } as DataSourceInstanceSettings);
const fetchMock = jest.fn().mockReturnValue(of({ data: { message: 'hello' } }));

jest.mock('@grafana/runtime', () => {
  const original = jest.requireActual('@grafana/runtime');
  const mockedRuntime = { ...original };

  mockedRuntime.getDataSourceSrv = () => {
    return {
      getInstanceSettings: settingsMock,
    };
  };

  mockedRuntime.getBackendSrv = () => ({
    fetch: fetchMock,
  });

  mockedRuntime.DataSourcePicker = MockPicker;

  return mockedRuntime;
});

describe('WriteTargetConfig', () => {
  it('renders the datasource picker and remote_write_target', async () => {
    const prometheusWriteTarget: PrometheusWriteTarget = {
      data_source_uid: 'test-uid',
      remote_write_path: 'test-path',
    };
    render(
      <WriteTargetConfigUnconnected
        navModel={{ node: {}, main: {} } as NavModel}
        prometheusWriteTarget={prometheusWriteTarget}
        getPrometheusWriteTarget={() => {}}
      />
    );

    expect(screen.getByDisplayValue('test-path')).toBeInTheDocument();

    await waitFor(() => {
      expect(settingsMock).toHaveBeenCalledWith('test-uid');
    });

    userEvent.click(screen.getByLabelText('Write target config save'));
    expect(screen.getByLabelText('Write target config save')).not.toBeDisabled();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith({
        method: 'POST',
        url: 'api/recording-rules/writer',
        data: { data_source_uid: 'test-datasource-uid', remote_write_path: 'test-path' },
        showSuccessAlert: false,
        showErrorAlert: false,
      });
    });
  });

  it('should disable save button if write target is not set', async () => {
    render(
      <WriteTargetConfigUnconnected
        navModel={{ node: {}, main: {} } as NavModel}
        prometheusWriteTarget={undefined}
        getPrometheusWriteTarget={() => {}}
      />
    );

    expect(screen.getByLabelText('Write target config save')).toBeDisabled();
  });
});
