import { Page } from 'puppeteer-core';
import { constants } from './constants';
import { PageObject } from './pageObjects';

export interface ExpectSelectorConfig {
  selector: string;
  containsText?: string;
  isVisible?: boolean;
}

export interface TestPageType<T> {
  init: (page: Page) => Promise<void>;
  getUrl: () => Promise<string>;
  getUrlWithoutBaseUrl: () => Promise<string>;
  navigateTo: () => Promise<void>;
  expectSelector: (config: ExpectSelectorConfig) => Promise<void>;
  waitForResponse: () => Promise<void>;
  waitForNavigation: () => Promise<void>;
  waitFor: (milliseconds: number) => Promise<void>;
  pageObjects: PageObjects<T>;
}

type PageObjects<T> = { [P in keyof T]: T[P] };

export interface TestPageConfig<T> {
  url?: string;
  pageObjects?: PageObjects<T>;
}

export class TestPage<T> implements TestPageType<T> {
  pageObjects: PageObjects<T> = null;
  private page: Page = null;
  private pageUrl: string = null;

  constructor(config: TestPageConfig<T>) {
    if (config.url) {
      this.pageUrl = `${constants.baseUrl}${config.url}`;
    }
    if (config.pageObjects) {
      this.pageObjects = config.pageObjects;
    }
  }

  init = async (page: Page): Promise<void> => {
    this.page = page;

    if (!this.pageObjects) {
      return;
    }

    Object.keys(this.pageObjects).forEach(key => {
      // @ts-ignore
      const pageObject: PageObject = this.pageObjects[key];
      pageObject.init(page);
    });
  };

  navigateTo = async (): Promise<void> => {
    this.throwIfNotInitialized();

    console.log('Trying to navigate to:', this.pageUrl);
    await this.page.goto(this.pageUrl);
  };

  expectSelector = async (config: ExpectSelectorConfig): Promise<void> => {
    this.throwIfNotInitialized();

    const { selector, containsText, isVisible } = config;
    const visible = isVisible || true;
    const text = containsText;
    const options = { visible, text } as any;
    await expect(this.page).toMatchElement(selector, options);
  };

  waitForResponse = async (): Promise<void> => {
    this.throwIfNotInitialized();

    await this.page.waitForResponse(response => response.url() === this.pageUrl && response.status() === 200);
  };

  waitForNavigation = async (): Promise<void> => {
    this.throwIfNotInitialized();

    await this.page.waitForNavigation();
  };

  getUrl = async (): Promise<string> => {
    this.throwIfNotInitialized();

    return await this.page.url();
  };

  getUrlWithoutBaseUrl = async (): Promise<string> => {
    this.throwIfNotInitialized();

    const url = await this.getUrl();

    return url.replace(constants.baseUrl, '');
  };

  waitFor = async (milliseconds: number) => {
    this.throwIfNotInitialized();

    await this.page.waitFor(milliseconds);
  };

  private throwIfNotInitialized = () => {
    if (!this.page) {
      throw new Error('pageFactory has not been initilized, did you forget to call init with a page?');
    }
  };
}
