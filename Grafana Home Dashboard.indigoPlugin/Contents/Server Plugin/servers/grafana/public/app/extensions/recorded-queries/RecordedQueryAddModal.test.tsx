import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import { act } from 'react-dom/test-utils';

import { DataSourceInstanceSettings, DataSourcePluginMeta, DataSourceRef, DataSourceSettings } from '@grafana/data';
import { DataSourcePickerProps, setEchoSrv } from '@grafana/runtime';
import { Echo } from 'app/core/services/echo/Echo';

import { IdDataQuery, RecordedQuery } from '../types';

import { filterRecordedQueries, RecordedQueryAddModalUnconnected } from './RecordedQueryAddModal';

function MockPicker(props: DataSourcePickerProps) {
  return <></>;
}

const settingsMock = jest
  .fn()
  .mockReturnValue({ id: 36, name: 'test name', uid: 'a', meta: { name: 'test', info: { logos: { small: '' } } } });

jest.mock('@grafana/runtime', () => {
  const original = jest.requireActual('@grafana/runtime');
  const mockedRuntime = { ...original };

  mockedRuntime.getDataSourceSrv = () => {
    return {
      getInstanceSettings: settingsMock,
    };
  };

  mockedRuntime.DataSourcePicker = MockPicker;

  return mockedRuntime;
});

beforeAll(() => {
  setEchoSrv(new Echo());
});

describe('with license and feature toggle', () => {
  it('renders the active recorded queries and the DataSourceFilter', () => {
    act(() => {
      render(
        <RecordedQueryAddModalUnconnected
          recordedQueries={queries}
          getRecordedQueriesAsync={() => {}}
          onChangeDataSource={() => {}}
          onAddQuery={() => {}}
          dataSource={dataSource}
        />
      );
    });

    userEvent.click(screen.getByText('Recorded query'));
    expect(screen.getByText('Add')).toBeInTheDocument();
    expect(screen.getByText('Recorded Query 1')).toBeInTheDocument();
    expect(screen.getByText('Recorded Query 3')).toBeInTheDocument();

    expect(screen.getByText('Filter by data source')).toBeInTheDocument();
  });

  it('filters datasources based on selected Datasource', () => {
    act(() => {
      render(
        <RecordedQueryAddModalUnconnected
          recordedQueries={queries}
          getRecordedQueriesAsync={() => {}}
          onChangeDataSource={() => {}}
          onAddQuery={() => {}}
          dataSource={dataSource}
          filterValue={{ id: 4, uid: 'a' } as DataSourceSettings}
        />
      );
    });

    userEvent.click(screen.getByText('Recorded query'));
    expect(screen.getByText('Add')).toBeInTheDocument();
    expect(screen.getByText('Recorded Query 1')).toBeInTheDocument();
    expect(screen.queryByText('Recorded Query 3')).not.toBeInTheDocument();

    expect(screen.getByText('Filter by data source')).toBeInTheDocument();
  });

  it('adds checked recorded queries', async () => {
    const addFn = jest.fn();
    act(() => {
      render(
        <RecordedQueryAddModalUnconnected
          recordedQueries={queries}
          getRecordedQueriesAsync={() => {}}
          onChangeDataSource={() => {}}
          onAddQuery={addFn}
          dataSource={dataSource}
          filterValue={{ id: 4, uid: 'a' } as DataSourceSettings}
        />
      );
    });

    userEvent.click(screen.getByText('Recorded query'));
    expect(screen.getByText('Add')).toBeInTheDocument();

    userEvent.click(screen.getAllByRole('checkbox')[0]);

    expect(screen.getByText('Add')).toBeEnabled();
    userEvent.click(screen.getByText('Add'));

    await waitFor(() => {
      expect(addFn).toHaveBeenCalledWith({
        datasource: '',
        exemplar: true,
        expr: 'Recorded Query 1{id="query-1", name="Recorded Query 1"}',
        interval: '',
        legendFormat: '',
      });
    });
  });
});
describe('filterRecordedQueries', () => {
  beforeEach(() => {
    settingsMock.mockImplementation((dsRef: DataSourceRef) => {
      if (dsRef.uid === 'a') {
        return { ...dataSource, uid: 'a', name: 'A-Prometheus', meta: { name: 'Prometheus' } };
      }
      if (dsRef.uid === 'b') {
        return { ...dataSource, uid: 'b', name: 'B-Prometheus', meta: { name: 'Prometheus' } };
      }
      return { ...dataSource, uid: 'c', name: 'GitHub', meta: { name: 'GitHub' } };
    });
  });

  it('filters and sorts based on ds type and rq name', () => {
    queries[1].active = true;
    const res = filterRecordedQueries(queries);
    expect(res[0].name).toBe('Recorded Query 3');
    expect(res[1].name).toBe('Recorded Query 1');
    expect(res[2].name).toBe('Recorded Query 2');
  });

  it('filters and sorts based on ds name and rq name', () => {
    queries[0].queries[0].datasource.uid = 'b';
    queries[1].active = true;
    const res = filterRecordedQueries(queries);
    expect(res[0].name).toBe('Recorded Query 3');
    expect(res[1].name).toBe('Recorded Query 2');
    expect(res[2].name).toBe('Recorded Query 1');
  });
});

const queries: RecordedQuery[] = [
  {
    id: 'query-1',
    target_ref_id: 'A',
    name: 'Recorded Query 1',
    prom_name: 'Recorded Query 1',
    description: 'desc',
    range: 21600,
    count: false,
    interval: 10,
    active: true,
    dest_data_source_uid: '',
    queries: [{ datasourceId: 4, datasource: { uid: 'a' } } as IdDataQuery],
  },
  {
    id: 'query-2',
    target_ref_id: 'A',
    name: 'Recorded Query 2',
    prom_name: 'Recorded Query 2',
    description: 'desc 2',
    range: 21600,
    count: true,
    interval: 10,
    active: false,
    dest_data_source_uid: '',
    queries: [{ datasourceId: 4, datasource: { uid: 'a' } } as IdDataQuery],
  },
  {
    id: 'query-3',
    target_ref_id: 'A',
    name: 'Recorded Query 3',
    prom_name: 'Recorded Query 3',
    description: 'desc 3',
    range: 21600,
    count: true,
    interval: 10,
    active: true,
    dest_data_source_uid: '',
    queries: [{ datasourceId: 2, datasource: { uid: 'c' } } as IdDataQuery],
  },
];

const dataSource: DataSourceInstanceSettings = {
  name: 'test data source',
  id: 4,
  uid: 'a',
  type: '',
  meta: { name: 'test' } as DataSourcePluginMeta,
  jsonData: {},
  access: 'direct',
};
