// Augment next-intl's Messages type with our translation shape
// so useTranslations() is fully typed.

import heMessages from '../../messages/he.json';

type Messages = typeof heMessages;

declare global {
  // eslint-disable-next-line @typescript-eslint/no-empty-interface
  interface IntlMessages extends Messages {}
}
