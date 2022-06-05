import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';

import { NavModel } from '@grafana/data';

import { IdDataQuery, RecordedQuery } from '../types';

import { RecordedQueriesConfigUnconnected } from './RecordedQueriesConfig';

describe('RecordedQueriesConfig', () => {
  const deleteFunc = jest.fn();
  const toggleActive = jest.fn();

  const setup = (queries: RecordedQuery[]) => {
    jest.resetAllMocks();

    render(
      <RecordedQueriesConfigUnconnected
        isLoading={false}
        navModel={{ node: {}, main: {} } as NavModel}
        recordedQueries={queries}
        getRecordedQueriesAsync={() => {}}
        updateRecordedQuery={toggleActive}
        deleteRecordedQuery={deleteFunc}
      />
    );
  };

  it('renders an empty list message when there are no recorded queries', () => {
    setup([]);

    expect(screen.getByText('No recorded queries defined')).toBeInTheDocument();
  });

  it('renders all of the recorded queries', () => {
    setup(queries);

    expect(screen.getAllByRole('button', { name: 'Pause recording' })).toHaveLength(2);
    expect(screen.getAllByRole('button', { name: 'Resume recording' })).toHaveLength(1);

    expect(screen.getByText('Recorded Query 1')).toBeInTheDocument();
    expect(screen.getByText('Recorded Query 2')).toBeInTheDocument();
    expect(screen.getByText('Recorded Query 3')).toBeInTheDocument();
  });

  it('calls the delete callback when deleting a recorded queries', async () => {
    setup(queries);

    userEvent.click(screen.getAllByRole('button', { name: 'Delete recorded query' })[0]);
    userEvent.click(screen.getAllByRole('button', { name: 'Confirm Modal Danger Button' })[0]);

    await waitFor(() => expect(deleteFunc).toHaveBeenCalledWith(queries[0]));
  });

  it('calls the toggle callback when activate or deactivate are called', () => {
    setup(queries);

    const toPause = screen.getAllByRole('button', { name: 'Pause recording' })[0];
    const toStart = screen.getAllByRole('button', { name: 'Resume recording' })[0];

    userEvent.click(toPause);
    userEvent.click(toStart);

    expect(toggleActive).toHaveBeenCalledWith({ ...queries[0], active: false });
    expect(toggleActive).toHaveBeenCalledWith({ ...queries[1], active: true });
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
    queries: [{ datasourceId: 4 } as IdDataQuery],
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
    queries: [{ datasourceId: 4 } as IdDataQuery],
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
    queries: [{ datasourceId: 2 } as IdDataQuery],
  },
];
