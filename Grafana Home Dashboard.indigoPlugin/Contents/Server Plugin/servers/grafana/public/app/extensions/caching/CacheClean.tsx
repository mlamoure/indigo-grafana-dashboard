import React, { useState } from 'react';

import { Button, ConfirmModal } from '@grafana/ui';

import { Props } from './DataSourceCache';

export const CacheClean = (props: Props) => {
  const { cleanCache, pageId } = props;
  const [showCleanModal, setShowCleanModal] = useState(false);

  const showConfirmCleanModal = (show: boolean) => () => {
    setShowCleanModal(show);
  };

  const handleCleanCache = () => {
    cleanCache(pageId);
    setShowCleanModal(false);
  };

  return (
    <div>
      <Button variant="destructive" onClick={showConfirmCleanModal(true)}>
        Clear cache
      </Button>
      <ConfirmModal
        isOpen={showCleanModal}
        title="Clear cache"
        body="Warning: This action impacts all cache-enabled data sources. If you are using Memcached, the system clears all data from the Memcached instance. Do you want to continue?"
        confirmText="Clear cache"
        onConfirm={handleCleanCache}
        onDismiss={showConfirmCleanModal(false)}
      />
    </div>
  );
};
