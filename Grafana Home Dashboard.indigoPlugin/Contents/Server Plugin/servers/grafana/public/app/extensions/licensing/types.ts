export interface LicenseToken {
  status: number;
  jti: string;
  iss: string;
  sub: string;
  iat: number;
  exp: number;
  nbf: number;
  lexp: number;
  lid: string;
  limit_by: string;
  included_admins: number;
  included_viewers: number;
  included_users: number;
  prod: string[];
  company: string;
  usage_billing?: boolean;
  slug: string;
  details_url?: string;
  account?: string;
  trial_exp?: number;
}

export interface ActiveUserStats {
  active_admins_and_editors: number;
  active_viewers: number;
  active_users: number;
}

export type PermissionsReport = {
  id: number;
  title: string;
  slug: string;
  uid: string;
  url: string;
  isFolder: boolean;
  orgId: number;
  granteeType: string;
  granteeName: string;
  granteeUrl: string;
  customPermissions: string;
  orgRole: string;
  usersCount: number;
};
