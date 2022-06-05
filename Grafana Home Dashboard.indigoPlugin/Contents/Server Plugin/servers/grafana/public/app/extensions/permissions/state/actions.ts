import { ThunkAction } from 'redux-thunk';

import { getBackendSrv } from 'app/core/services/backend_srv';
import { StoreState } from 'app/types';

import { DataSourcePermissionDTO } from '../../types';

export enum ActionTypes {
  LoadDataSourcePermissions = 'LOAD_DATA_SOURCE_PERMISSIONS',
}

export interface LoadDataSourcePermissionsAction {
  type: ActionTypes.LoadDataSourcePermissions;
  payload: DataSourcePermissionDTO;
}

const dataSourcePermissionsLoaded = (
  dataSourcePermission: DataSourcePermissionDTO
): LoadDataSourcePermissionsAction => ({
  type: ActionTypes.LoadDataSourcePermissions,
  payload: dataSourcePermission,
});

export type Action = LoadDataSourcePermissionsAction;

type ThunkResult<R> = ThunkAction<R, StoreState, undefined, Action>;

export function loadDataSourcePermissions(id: number): ThunkResult<void> {
  return async (dispatch) => {
    const response = await getBackendSrv().get(`/api/datasources/${id}/permissions`);
    dispatch(dataSourcePermissionsLoaded(response));
  };
}

export function enableDataSourcePermissions(id: number): ThunkResult<void> {
  return async (dispatch) => {
    await getBackendSrv().post(`/api/datasources/${id}/enable-permissions`, {});
    dispatch(loadDataSourcePermissions(id));
  };
}

export function disableDataSourcePermissions(id: number): ThunkResult<void> {
  return async (dispatch) => {
    await getBackendSrv().post(`/api/datasources/${id}/disable-permissions`, {});
    dispatch(loadDataSourcePermissions(id));
  };
}

export function addDataSourcePermission(id: number, data: object): ThunkResult<void> {
  return async (dispatch) => {
    await getBackendSrv().post(`/api/datasources/${id}/permissions`, data);

    dispatch(loadDataSourcePermissions(id));
  };
}

export function removeDataSourcePermission(id: number, permissionId: number): ThunkResult<void> {
  return async (dispatch) => {
    await getBackendSrv().delete(`/api/datasources/${id}/permissions/${permissionId}`);
    dispatch(loadDataSourcePermissions(id));
  };
}
