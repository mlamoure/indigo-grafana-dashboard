import { css } from '@emotion/css';
import history from 'history';
import React, { useEffect, useState } from 'react';
import { Prompt, Redirect } from 'react-router-dom';

import { reportInteraction } from '@grafana/runtime/src';
import { Button, Modal } from '@grafana/ui';
import { Report } from 'app/extensions/types';

import { BASE_URL } from '../constants';
import { reportSteps } from '../index';
import { scheduleUpdated } from '../utils/scheduler';

export interface Props {
  confirmRedirect?: boolean;
  onDiscard: () => void;
  report: Report;
}

/**
 * Component handling redirects when report form has unsaved changes.
 * Page reloads are handled in useEffect via beforeunload event.
 * URL navigation is handled by react-router's components since it does not trigger beforeunload event.
 */
export const ReportFormPrompt = ({ confirmRedirect, onDiscard, report }: Props) => {
  const [modalIsOpen, setModalIsOpen] = useState(false);
  const [blockedLocation, setBlockedLocation] = useState<history.Location | null>(null);
  const [changesDiscarded, setChangesDiscarded] = useState(false);

  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (confirmRedirect) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', onBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', onBeforeUnload);
    };
  }, [confirmRedirect]);

  // Returning 'false' from this function will prevent navigation to the next URL
  const handleRedirect = (location: history.Location) => {
    const reportFormUrls = reportSteps.map((step) => `${BASE_URL}/${step.id}`);
    const navigationOutsideForm = !reportFormUrls.includes(location.pathname);

    if (confirmRedirect && navigationOutsideForm && !changesDiscarded) {
      setModalIsOpen(true);
      setBlockedLocation(location);
      return false;
    }

    // Clear form state if no changes to the form have been made
    if (navigationOutsideForm) {
      onDiscard();
    }

    return true;
  };

  const onBackToForm = () => {
    setModalIsOpen(false);
    setBlockedLocation(null);
  };

  const onDiscardChanges = () => {
    reportInteraction('reports_report_abandoned', {
      namePopulated: !!report.name,
      recipientsPopulated: !!report.recipients,
      replyToPopulated: !!report.replyTo,
      dashboardSelected: !!report.dashboardUid,
      timeRangeSelected: !!report.options.timeRange.from,
      scheduleCustomized: scheduleUpdated(report.schedule),
    });
    setModalIsOpen(false);
    setChangesDiscarded(true);
    onDiscard();
  };

  return (
    <>
      <Prompt when={true} message={handleRedirect} />
      {blockedLocation && changesDiscarded && <Redirect to={blockedLocation} />}
      <UnsavedChangesModal isOpen={modalIsOpen} onDiscard={onDiscardChanges} onBackToForm={onBackToForm} />
    </>
  );
};

interface UnsavedChangesModalProps {
  onDiscard: () => void;
  onBackToForm: () => void;
  isOpen: boolean;
}

const UnsavedChangesModal = ({ onDiscard, onBackToForm, isOpen }: UnsavedChangesModalProps) => {
  return (
    <Modal
      isOpen={isOpen}
      title="Leave page?"
      onDismiss={onBackToForm}
      icon="exclamation-triangle"
      className={css`
        width: 500px;
      `}
    >
      <h5>Changes that you made may not be saved.</h5>
      <Modal.ButtonRow>
        <Button variant="secondary" onClick={onBackToForm} fill="outline">
          Continue editing
        </Button>
        <Button variant="destructive" onClick={onDiscard}>
          Discard unsaved changes
        </Button>
      </Modal.ButtonRow>
    </Modal>
  );
};
