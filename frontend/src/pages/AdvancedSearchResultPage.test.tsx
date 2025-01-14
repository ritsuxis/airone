/**
 * @jest-environment jsdom
 */

import {
  render,
  waitForElementToBeRemoved,
  screen,
} from "@testing-library/react";
import React from "react";

import { AdvancedSearchResultsPage } from "pages/AdvancedSearchResultsPage";
import { TestWrapper } from "utils/TestWrapper";

afterEach(() => {
  jest.clearAllMocks();
});

test("should match snapshot", async () => {
  Object.defineProperty(window, "django_context", {
    value: {
      user: {
        is_superuser: false,
      },
    },
    writable: false,
  });

  const results = [
    {
      entry: {
        name: "entry1",
      },
      attrs: {
        attr1: {
          type: 2,
          value: { as_string: "attr1" },
        },
        attr2: {
          type: 2,
          value: { as_string: "attr1" },
        },
      },
    },
  ];

  /* eslint-disable */
  jest
    .spyOn(
      require("apiclient/AironeApiClientV2").aironeApiClientV2,
      "advancedSearchEntries"
    )
    .mockResolvedValue({
      json() {
        return Promise.resolve({
          result: {
            ret_values: results,
          },
        });
      },
    });
  /* eslint-enable */

  // wait async calls and get rendered fragment
  const result = render(<AdvancedSearchResultsPage />, {
    wrapper: TestWrapper,
  });
  await waitForElementToBeRemoved(screen.getByTestId("loading"));

  expect(result).toMatchSnapshot();
});
