import { render, screen } from '@testing-library/react';
import React from 'react';

import { DataSourcePermission } from '../types';

import { DataSourcePermissionsList, Props } from './DataSourcePermissionsList';
import {
  getMockDataSourcePermissionsTeam,
  getMockDataSourcePermissionsUser,
} from './__mocks__/dataSourcePermissionMocks';

jest.mock('app/core/core', () => {
  return {
    contextSrv: {
      hasPermission: () => true,
    },
  };
});

const setup = (propOverrides?: object) => {
  const props: Props = {
    items: [] as DataSourcePermission[],
    onRemoveItem: jest.fn(),
  };

  Object.assign(props, propOverrides);

  render(<DataSourcePermissionsList {...props} />);
};

describe('Render', () => {
  it('should render component', () => {
    setup();

    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getAllByRole('row')).toHaveLength(1);
  });

  it('should render items', () => {
    setup({
      items: [getMockDataSourcePermissionsUser(), getMockDataSourcePermissionsTeam()],
    });

    expect(screen.getAllByRole('row')).toHaveLength(3);
    expect(screen.getAllByAltText('Avatar for user 3')).toHaveLength(1);
    expect(screen.getAllByAltText('Avatar for team 1')).toHaveLength(1);
  });
});
