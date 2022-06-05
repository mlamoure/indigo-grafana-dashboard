import { render, screen } from '@testing-library/react';
import React from 'react';
import selectEvent from 'react-select-event';

import { AclTarget } from 'app/types';

import { AddDataSourcePermissions, Props } from './AddDataSourcePermissions';

jest.mock('app/core/core', () => {
  return {
    contextSrv: {
      hasPermission: () => true,
    },
  };
});

jest.mock('@grafana/runtime', () => ({
  getBackendSrv: () => {
    return {
      get: () => {
        return Promise.resolve([]);
      },
    };
  },
  config: {
    featureToggles: {},
  },
}));

beforeEach(() => {
  jest.clearAllMocks();
});

const setup = () => {
  const props: Props = {
    onAddPermission: jest.fn(),
    onCancel: jest.fn(),
  };

  render(<AddDataSourcePermissions {...props} />);
};

const selectTarget = async (target: string) => {
  await selectEvent.select(screen.getByLabelText('Role to add new permission to'), target, {
    container: document.body,
  });
};

describe('Render', () => {
  it('should render component', async () => {
    setup();

    expect(await screen.findByText(/add permission for/i)).toBeInTheDocument();
  });

  it('should render user picker', async () => {
    setup();

    await selectTarget(AclTarget.User);
    expect(await screen.findByTestId('userPicker')).toBeInTheDocument();
  });

  it('should render team picker', async () => {
    setup();

    await selectTarget(AclTarget.Team);
    expect(await screen.findByTestId('teamPicker')).toBeInTheDocument();
  });
});
