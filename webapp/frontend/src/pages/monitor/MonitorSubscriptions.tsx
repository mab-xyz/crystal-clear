import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";

import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { Label } from "@/shared/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/shared/components/ui/alert";
import { useLocalAlert } from "@/shared/components/ui";
import { useAppContext } from "@/app/contexts/AppContext";
import { subscribeToContract, unsubscribeFromContract } from "@/domains/monitoring";
import type {
  MonitoringAction,
  MonitoringRequest,
  MonitoringResult,
} from "@/types";
import { validateEthereumAddress } from "@/shared/utils/validation";

import styles from "./MonitorSubscriptions.module.css";

type FormStatus = "idle" | "loading" | "success" | "error";

type ActionDescriptor = {
  value: MonitoringAction;
  label: string;
  description: string;
};

const NOTIFICATION_METHOD: MonitoringRequest["method"] = "email";

const MAX_EMAIL_LENGTH = 320;
const MAX_CONTRACT_LENGTH = 42;

const EMAIL_PATTERN = /[^\s@]+@[^\s@]+\.[^\s@]+/;

const FORM_COPY = {
  title: "Monitor contract upgrade",
  description:
    "Subscribe to email alerts for important changes to your smart contracts.",
  emailLabel: "Email",
  emailPlaceholder: "name@company.com",
  contractLabel: "Contract address",
  contractPlaceholder: "0x000...",
  consentLabel: "I want to receive email notifications for this contract.",
  successTitle: "Request successful",
  errorTitle: "Request failed",
  subscribeSuccess: "You're now subscribed to alerts for this contract.",
  unsubscribeSuccess: "You're no longer subscribed to alerts for this contract.",
  subscribeCta: "Subscribe",
  unsubscribeCta: "Unsubscribe",
  backCta: "Back to dashboard",
};

const ACTIONS: ActionDescriptor[] = [
  {
    value: "subscribe",
    label: "Subscribe",
    description: "Receive email alerts when the contract state changes.",
  },
  {
    value: "unsubscribe",
    label: "Unsubscribe",
    description: "Stop receiving notifications for this contract.",
  },
];

const normalizeEmail = (value: string) => value.trim().toLowerCase();
const normalizeContract = (value: string) => value.trim();
const isValidEmail = (value: string) => EMAIL_PATTERN.test(value.trim());

const buildPayload = (
  email: string,
  contractAddress: string,
): MonitoringRequest => ({
  method: NOTIFICATION_METHOD,
  target: email,
  contractAddress,
});

export default function MonitorSubscriptionsPage(): JSX.Element {
  const navigate = useNavigate();
  const { showLocalAlert } = useLocalAlert();
  const { setGlobalError, clearGlobalError } = useAppContext();

  const [action, setAction] = useState<MonitoringAction>("subscribe");
  const [email, setEmail] = useState<string>("");
  const [contractAddress, setContractAddress] = useState<string>("");
  const [consent, setConsent] = useState<boolean>(false);
  const [formStatus, setFormStatus] = useState<FormStatus>("idle");
  const [statusMessage, setStatusMessage] = useState<string>("");

  const normalizedEmail = useMemo(() => normalizeEmail(email), [email]);
  const normalizedContract = useMemo(
    () => normalizeContract(contractAddress),
    [contractAddress],
  );
  const contractValidation = useMemo(
    () => validateEthereumAddress(normalizedContract),
    [normalizedContract],
  );
  const {
    isValid: contractIsValid,
    error: contractError,
    sanitized: sanitizedContract,
  } = contractValidation;

  const consentRequired = action === "subscribe";

  useEffect(() => {
    if (typeof document === "undefined") {
      return undefined;
    }

    const previousBackground = document.body.style.backgroundColor;
    document.body.style.backgroundColor = "#ffffff";

    return () => {
      document.body.style.backgroundColor = previousBackground;
    };
  }, []);

  const disabledReason = useMemo(() => {
    if (formStatus === "loading") {
      return "Submitting request…";
    }

    if (!email.trim()) {
      return "Enter your email address to continue.";
    }

    if (!isValidEmail(normalizedEmail)) {
      return "Please enter a valid email address.";
    }

    if (!normalizedContract) {
      return "Enter a contract address to continue.";
    }

    if (!contractIsValid) {
      return contractError || "Invalid Ethereum contract address.";
    }

    if (consentRequired && !consent) {
      return "Check the consent box to enable email alerts.";
    }

    return null;
  }, [
    formStatus,
    email,
    normalizedEmail,
    normalizedContract,
    contractIsValid,
    contractError,
    consentRequired,
    consent,
  ]);

  const resetStatus = () => {
    if (formStatus !== "idle") {
      setFormStatus("idle");
      setStatusMessage("");
      clearGlobalError();
    }
  };

  const handleActionChange = (nextAction: MonitoringAction) => {
    setAction(nextAction);
    setStatusMessage("");
    setFormStatus("idle");
    clearGlobalError();
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    clearGlobalError();

    if (!isValidEmail(normalizedEmail)) {
      const message = "Please enter a valid email address.";
      setFormStatus("error");
      setStatusMessage(message);
      showLocalAlert(message);
      setGlobalError(message);
      return;
    }

    if (!normalizedContract) {
      const message = "Contract address is required.";
      setFormStatus("error");
      setStatusMessage(message);
      showLocalAlert(message);
      setGlobalError(message);
      return;
    }

    if (!contractIsValid) {
      const message = contractError || "Invalid Ethereum contract address.";
      setFormStatus("error");
      setStatusMessage(message);
      showLocalAlert(message);
      setGlobalError(message);
      return;
    }

    if (consentRequired && !consent) {
      const message = "Please allow email notifications to subscribe.";
      setFormStatus("error");
      setStatusMessage(message);
      showLocalAlert(message);
      setGlobalError(message);
      return;
    }

    setFormStatus("loading");
    setStatusMessage("");

    const payload = buildPayload(
      normalizedEmail,
      sanitizedContract ?? normalizedContract,
    );

    const result: MonitoringResult =
      action === "subscribe"
        ? await subscribeToContract(payload)
        : await unsubscribeFromContract(payload);

    if (!result.ok) {
      const message = result.error || "Unexpected error.";
      setFormStatus("error");
      setStatusMessage(message);
      showLocalAlert(message);
      setGlobalError(message);
      return;
    }

    const message =
      result.message ||
      (action === "subscribe"
        ? FORM_COPY.subscribeSuccess
        : FORM_COPY.unsubscribeSuccess);

    setFormStatus("success");
    setStatusMessage(message);
    showLocalAlert(message);

    if (action === "subscribe") {
      setConsent(false);
    }

    setContractAddress("");
  };

  const submitDisabled =
    formStatus === "loading" ||
    !isValidEmail(normalizedEmail) ||
    !normalizedContract ||
    !contractIsValid ||
    (consentRequired && !consent);

  return (
    <div className={styles.page}>
      <main className={styles.card}>
        <header className={styles.header}>
          <h1 className={styles.title}>{FORM_COPY.title}</h1>
          <p className={styles.description}>{FORM_COPY.description}</p>
        </header>

        <form className={styles.form} onSubmit={handleSubmit}>
          <fieldset className={styles.actions}>
            <legend className={styles.legend}>Action</legend>
            <div className={styles.actionList}>
              {ACTIONS.map((item) => {
                const isActive = item.value === action;
                const isUnsubscribe = item.value === "unsubscribe";
                const optionClassNames = [
                  styles.actionOption,
                  isActive ? styles.actionOptionActive : "",
                  isUnsubscribe ? styles.actionOptionUnsubscribe : "",
                  isActive && isUnsubscribe
                    ? styles.actionOptionUnsubscribeActive
                    : "",
                ]
                  .filter(Boolean)
                  .join(" ");
                return (
                  <label
                    key={item.value}
                    className={optionClassNames}
                  >
                    <input
                      type="radio"
                      name="monitor-action"
                      value={item.value}
                      checked={isActive}
                      onChange={() => handleActionChange(item.value)}
                      className={styles.actionInput}
                    />
                    <span
                      className={
                        isUnsubscribe
                          ? `${styles.actionLabel} ${styles.actionLabelUnsubscribe}`
                          : styles.actionLabel
                      }
                    >
                      {item.label}
                    </span>
                    <span
                      className={
                        isUnsubscribe
                          ? `${styles.actionDescription} ${styles.actionDescriptionUnsubscribe}`
                          : styles.actionDescription
                      }
                    >
                      {item.description}
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>

          <div className={styles.field}>
            <Label htmlFor="monitor-email" className={styles.label}>
              {FORM_COPY.emailLabel}
            </Label>
            <Input
              id="monitor-email"
              type="email"
              autoComplete="email"
              placeholder={FORM_COPY.emailPlaceholder}
              value={email}
              onChange={(event) => {
                const next = event.target.value.slice(0, MAX_EMAIL_LENGTH);
                setEmail(next);
                resetStatus();
              }}
              aria-invalid={formStatus === "error" && !isValidEmail(normalizedEmail)}
              maxLength={MAX_EMAIL_LENGTH}
            />
          </div>

          <div className={styles.field}>
            <Label htmlFor="monitor-contract" className={styles.label}>
              {FORM_COPY.contractLabel}
            </Label>
            <Input
              id="monitor-contract"
              placeholder={FORM_COPY.contractPlaceholder}
              value={contractAddress}
              onChange={(event) => {
                const next = event.target.value.slice(0, MAX_CONTRACT_LENGTH);
                setContractAddress(next);
                resetStatus();
              }}
              aria-invalid={
                formStatus === "error" &&
                (!normalizedContract.length || !contractIsValid)
              }
              maxLength={MAX_CONTRACT_LENGTH}
            />
          </div>

          <div className={styles.field}>
            <div className={styles.consentRow}>
              <Checkbox
                id="monitor-consent"
                checked={consent}
                onCheckedChange={(nextValue) => {
                  setConsent(nextValue === true);
                  resetStatus();
                }}
                aria-invalid={formStatus === "error" && consentRequired && !consent}
              />
              <Label htmlFor="monitor-consent" className={styles.label}>
                {FORM_COPY.consentLabel}
              </Label>
            </div>
          </div>

          <div className={styles.feedback}>
            {formStatus === "success" && statusMessage ? (
              <Alert>
                <AlertTitle>{FORM_COPY.successTitle}</AlertTitle>
                <AlertDescription>{statusMessage}</AlertDescription>
              </Alert>
            ) : null}

            {formStatus === "error" && statusMessage ? (
              <Alert variant="destructive">
                <AlertTitle>{FORM_COPY.errorTitle}</AlertTitle>
                <AlertDescription>{statusMessage}</AlertDescription>
              </Alert>
            ) : null}
          </div>

          <div className={styles.actionsRow}>
            {submitDisabled && disabledReason ? (
              <p className={styles.hint} role="note">
                {disabledReason}
              </p>
            ) : null}
            <div className={styles.actionButtons}>
              <Button
                type="submit"
                disabled={submitDisabled}
                aria-disabled={submitDisabled}
                variant="default"
                className={
                  action === "unsubscribe"
                    ? `${styles.actionButton} ${styles.actionButtonDestructive}`
                    : `${styles.actionButton} ${styles.actionButtonPrimary}`
                }
              >
                {formStatus === "loading"
                  ? "Submitting…"
                  : action === "subscribe"
                  ? FORM_COPY.subscribeCta
                  : FORM_COPY.unsubscribeCta}
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() => navigate("/")}
                className={`${styles.actionButton} ${styles.actionButtonGhost}`}
              >
                {FORM_COPY.backCta}
              </Button>
            </div>
          </div>
        </form>
      </main>
    </div>
  );
}
