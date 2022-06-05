import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import { of, throwError } from 'rxjs';

import { DataQuery, DataSourceInstanceSettings, DataSourceRef } from '@grafana/data';
import { setEchoSrv } from '@grafana/runtime';
import { selectOptionInTest } from '@grafana/ui';
import { Echo } from 'app/core/services/echo/Echo';

import { CreateRecordedQueryUnconnected } from './RecordedQueryCreateModal';

const fetchMock = jest.fn().mockReturnValue(of({ data: { message: 'hello' } }));
const settingsMock = jest.fn().mockReturnValue({ id: 36 });

jest.mock('app/core/core', () => ({
  contextSrv: {
    hasAccess: (action: string, fallBack: boolean) => true,
    hasRole: (role: string) => true,
  },
}));

jest.mock('@grafana/runtime', () => {
  const original = jest.requireActual('@grafana/runtime');
  const mockedRuntime = { ...original };

  mockedRuntime.getDataSourceSrv = () => {
    return {
      get: settingsMock,
    };
  };

  mockedRuntime.getBackendSrv = () => ({
    fetch: fetchMock,
  });

  return mockedRuntime;
});

beforeAll(() => {
  setEchoSrv(new Echo());
});

describe('RecordedQueryCreateModal', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    fetchMock.mockReturnValue(of({ data: { message: 'hello' } }));
    settingsMock.mockReturnValue({ id: 36 });
  });

  describe('with license and feature toggle', () => {
    it('validates the form for required values', async () => {
      render(<CreateRecordedQueryUnconnected onChangeDataSource={() => {}} variables={[]} dispatch={{} as any} />);

      userEvent.click(screen.getByTitle('Create recorded query'));
      userEvent.click(screen.getByText('Start recording query'));

      await waitFor(() => {
        expect(screen.getByText('Name is required')).toBeInTheDocument();
      });
    });

    it('posts a recording rule with existing queries to the backend endpoint', async () => {
      const query: DataQuery = { refId: 'A' };
      const queries: Array<Partial<DataQuery>> = [{ refId: 'A' }];
      const dataSource = { name: 'ds-name' } as DataSourceInstanceSettings;

      render(
        <CreateRecordedQueryUnconnected
          query={query}
          queries={queries}
          dataSource={dataSource}
          onChangeDataSource={() => {}}
          variables={[]}
          dispatch={{} as any}
        />
      );
      await fillRecordedQueryForm();

      userEvent.click(screen.getByText('Start recording query'));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledWith({ ...rrQuery, url: 'api/recording-rules', showErrorAlert: false });
      });
    });

    it('posts a recording rule to the test backend endpoint', async () => {
      const query: DataQuery = { refId: 'A' };
      const queries: Array<Partial<DataQuery>> = [{ refId: 'A' }];
      const dataSource = { name: 'ds-name' } as DataSourceInstanceSettings;

      render(
        <CreateRecordedQueryUnconnected
          query={query}
          queries={queries}
          dataSource={dataSource}
          onChangeDataSource={() => {}}
          variables={[]}
          dispatch={{} as any}
        />
      );

      await fillRecordedQueryForm();

      userEvent.click(screen.getByLabelText('Test the recorded query'));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledWith({
          ...rrQuery,
          url: 'api/recording-rules/test',
          showSuccessAlert: false,
          showErrorAlert: false,
        });
      });
    });

    it('displays a link to support when an unknown error occurs', async () => {
      const mv = { data: { message: 'An unknown issue is preventing the system from processing your query.' } };
      fetchMock.mockReturnValue(throwError(() => mv));

      const query: DataQuery = { refId: 'A' };
      const queries: Array<Partial<DataQuery>> = [{ refId: 'A' }];
      const dataSource = { name: 'ds-name' } as DataSourceInstanceSettings;

      render(
        <CreateRecordedQueryUnconnected
          query={query}
          queries={queries}
          dataSource={dataSource}
          onChangeDataSource={() => {}}
          variables={[]}
          dispatch={{} as any}
        />
      );

      await fillRecordedQueryForm();

      userEvent.click(screen.getByLabelText('Test the recorded query'));

      await waitFor(() => {
        expect(screen.getByText('Contact Grafana Labs')).toBeInTheDocument();
      });
    });

    it('displays success message when recording is successful', async () => {
      const query: DataQuery = { refId: 'A' };
      const queries: Array<Partial<DataQuery>> = [{ refId: 'A' }];
      const dataSource = { name: 'ds-name' } as DataSourceInstanceSettings;

      render(
        <CreateRecordedQueryUnconnected
          query={query}
          queries={queries}
          dataSource={dataSource}
          onChangeDataSource={() => {}}
          variables={[]}
          dispatch={{} as any}
        />
      );

      await fillRecordedQueryForm();

      userEvent.click(screen.getByText('Start recording query'));

      await waitFor(() => {
        expect(screen.getByText('Your new recorded query is recording successfully!')).toBeInTheDocument();
        expect(screen.getByText('Close')).toBeInTheDocument();
        expect(screen.queryByText('Start recording query')).not.toBeInTheDocument();
      });
    });

    it('uses the data source name from the query if it exists', async () => {
      const query: DataQuery = { refId: 'A' };
      const ref: DataSourceRef = { uid: 'query-datasource' };
      const queries: Array<Partial<DataQuery>> = [{ refId: 'A', datasource: ref }];
      const dataSource = { name: 'ds-name' } as DataSourceInstanceSettings;

      render(
        <CreateRecordedQueryUnconnected
          query={query}
          queries={queries}
          dataSource={dataSource}
          onChangeDataSource={() => {}}
          variables={[]}
          dispatch={{} as any}
        />
      );
      await fillRecordedQueryForm();

      userEvent.click(screen.getByText('Start recording query'));

      await waitFor(() => {
        expect(settingsMock).toHaveBeenCalledWith(ref);
      });
    });
  });
});

async function fillRecordedQueryForm() {
  userEvent.click(screen.getByTitle('Create recorded query'));

  const intervalSelect = screen.getByLabelText('Interval-select');

  userEvent.type(screen.getByRole('textbox', { name: 'Name * Give this query a name' }), 'q-name');
  userEvent.type(screen.getByRole('textbox', { name: 'Description Provide a description for this query' }), 'desc');
  await selectOptionInTest(intervalSelect, '30 minutes');

  userEvent.click(screen.getByText('now-10m to now'));
  userEvent.click(screen.getByText('Last 12 hours'));
  userEvent.click(screen.getByRole('checkbox'));
}

const rrQuery = {
  data: {
    active: true,
    count: true,
    description: 'desc',
    interval: 1800,
    name: 'q-name',
    queries: [
      {
        datasourceId: 36,
        refId: 'A',
      },
    ],
    range: 43200,
    target_ref_id: 'A',
  },
  method: 'POST',
};
