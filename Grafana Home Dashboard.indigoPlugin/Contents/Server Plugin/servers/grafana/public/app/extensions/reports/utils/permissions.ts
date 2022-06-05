import { contextSrv } from 'app/core/core';

import { AccessControlAction } from '../../types';

export const canEditReport =
  contextSrv.hasPermission(AccessControlAction.ReportingAdminWrite) ||
  contextSrv.hasPermission(AccessControlAction.ReportingAdminCreate);
