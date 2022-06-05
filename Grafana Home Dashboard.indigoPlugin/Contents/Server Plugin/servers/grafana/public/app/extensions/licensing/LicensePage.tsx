import React, { useEffect, useState } from 'react';
import { connect, ConnectedProps } from 'react-redux';

import { config } from '@grafana/runtime';
import Page from 'app/core/components/Page/Page';
import { GrafanaRouteComponentProps } from 'app/core/navigation/types';
import { getNavModel } from 'app/core/selectors/navModel';
import { contextSrv } from 'app/core/services/context_srv';
import { ServerStats } from 'app/features/admin/ServerStats';

import { AccessControlAction, EnterpriseStoreState } from '../types';

import { LicenseInfo } from './LicenseInfo';
import { getLicenseToken, refreshLicenseStats } from './state/api';
import { ActiveUserStats, LicenseToken } from './types';

import { initLicenseWarnings } from './index';

interface QueryParams {
  tokenUpdated?: boolean;
  tokenRenewed?: boolean;
}

interface OwnProps extends GrafanaRouteComponentProps<{}, QueryParams> {}

const mapStateToProps = (state: EnterpriseStoreState) => ({
  navModel: getNavModel(state.navIndex, 'licensing'),
});

const connector = connect(mapStateToProps, {});
export type Props = ConnectedProps<typeof connector> & OwnProps;

export const LicensePage = ({ navModel, queryParams }: Props) => {
  const [token, setToken] = useState<LicenseToken | null>(null);
  const [stats, setStats] = useState<ActiveUserStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const { tokenUpdated, tokenRenewed } = queryParams;

  useEffect(() => {
    if (!contextSrv.hasAccess(AccessControlAction.LicensingRead, contextSrv.isGrafanaAdmin)) {
      return;
    }

    setIsLoading(true);
    const getData = async () => {
      const token = await getLicenseToken().catch(() => null);
      const stats = await refreshLicenseStats().catch(() => null);
      setToken(token);
      setStats(stats);
      setIsLoading(false);
    };
    getData();

    return initLicenseWarnings;
  }, []);

  return (
    <Page navModel={navModel}>
      <Page.Contents>
        <ServerStats />
        <LicenseInfo
          token={token}
          stats={stats}
          tokenUpdated={tokenUpdated}
          tokenRenewed={tokenRenewed}
          isLoading={isLoading}
          licensedUrl={(config as any).licenseInfo?.appUrl}
        />
      </Page.Contents>
    </Page>
  );
};

export default connector(LicensePage);
