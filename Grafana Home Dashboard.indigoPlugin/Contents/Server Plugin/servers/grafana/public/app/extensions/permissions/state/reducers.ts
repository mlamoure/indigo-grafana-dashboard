import { DataSourcePermission, DataSourcePermissionState } from '../../types';

import { Action, ActionTypes } from './actions';

const initialState: DataSourcePermissionState = {
  permissions: [] as DataSourcePermission[],
  enabled: false,
  datasourceId: 0,
};

export const dataSourcePermissionReducers = (state = initialState, action: Action): DataSourcePermissionState => {
  switch (action.type) {
    case ActionTypes.LoadDataSourcePermissions:
      return {
        enabled: action.payload.enabled,
        permissions: action.payload.permissions,
        datasourceId: action.payload.datasourceId,
      };
  }

  return state;
};

export default {
  dataSourcePermission: dataSourcePermissionReducers,
};
