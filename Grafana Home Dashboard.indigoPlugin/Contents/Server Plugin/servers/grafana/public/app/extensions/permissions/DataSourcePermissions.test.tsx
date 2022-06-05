import { render, screen } from '@testing-library/react';
import React from 'react';

import { NavModel } from '@grafana/data';

import { DataSourcePermission } from '../types';

import { DataSourcePermissions, Props } from './DataSourcePermissions';

jest.mock('app/core/core', () => {
  return {
    contextSrv: {
      hasPermission: () => true,
    },
  };
});

jest.mock('app/features/plugins/datasource_srv', () => {
  return {
    getDatasourceSrv: () => {
      return {};
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
    buildInfo: {},
    licenseInfo: {},
    getConfig: () => {},
    config: {},
    featureToggles: {},
  },
}));

jest.mock('@grafana/runtime/src/config', () => ({
  config: {
    buildInfo: {},
    licenseInfo: {},
    getConfig: () => {},
    config: {},
    featureToggles: {},
  },
}));

beforeEach(() => {
  jest.clearAllMocks();
});

const setup = (propOverrides?: object) => {
  const props: Props = {
    permissions: [] as DataSourcePermission[],
    enabled: true,
    isDefault: false,
    uid: '1',
    navModel: { node: {}, main: {} } as NavModel,
    addDataSourcePermission: jest.fn(),
    enableDataSourcePermissions: jest.fn(),
    disableDataSourcePermissions: jest.fn(),
    loadDataSourcePermissions: jest.fn(),
    loadDataSource: async () => jest.fn((uid: string) => ({ id: 1 } as any)) as any,
    loadDataSourceMeta: jest.fn(),
    removeDataSourcePermission: jest.fn(),
  };

  Object.assign(props, propOverrides);

  render(<DataSourcePermissions {...props} />);
};

describe('Render', () => {
  it('should render component', () => {
    setup({ enabled: false });

    expect(screen.getByText('Enable')).toBeInTheDocument();
  });

  it('should render permissions enabled', async () => {
    setup({
      dataSourcePermission: {
        enabled: true,
        uid: '1',
        permissions: [] as DataSourcePermission[],
      },
    });

    expect(await screen.findByRole('button', { name: /Add a permission/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Disable permissions/i })).toBeInTheDocument();
  });
});
