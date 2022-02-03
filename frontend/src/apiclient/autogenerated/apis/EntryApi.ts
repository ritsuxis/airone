/* tslint:disable */
/* eslint-disable */
/**
 *
 * No description provided (generated by Openapi Generator https://github.com/openapitools/openapi-generator)
 *
 * The version of the OpenAPI document: 0.0.0
 *
 *
 * NOTE: This class is auto generated by OpenAPI Generator (https://openapi-generator.tech).
 * https://openapi-generator.tech
 * Do not edit the class manually.
 */

import * as runtime from "../runtime";
import { Entry, EntryFromJSON, EntryToJSON } from "../models";

export interface EntryApiV2RetrieveRequest {
  id: number;
}

/**
 *
 */
export class EntryApi extends runtime.BaseAPI {
  /**
   */
  async entryApiV2RetrieveRaw(
    requestParameters: EntryApiV2RetrieveRequest,
    initOverrides?: RequestInit
  ): Promise<runtime.ApiResponse<Entry>> {
    if (requestParameters.id === null || requestParameters.id === undefined) {
      throw new runtime.RequiredError(
        "id",
        "Required parameter requestParameters.id was null or undefined when calling entryApiV2Retrieve."
      );
    }

    const queryParameters: any = {};

    const headerParameters: runtime.HTTPHeaders = {};

    if (
      this.configuration &&
      (this.configuration.username !== undefined ||
        this.configuration.password !== undefined)
    ) {
      headerParameters["Authorization"] =
        "Basic " +
        btoa(this.configuration.username + ":" + this.configuration.password);
    }
    const response = await this.request(
      {
        path: `/entry/api/v2/{id}`.replace(
          `{${"id"}}`,
          encodeURIComponent(String(requestParameters.id))
        ),
        method: "GET",
        headers: headerParameters,
        query: queryParameters,
      },
      initOverrides
    );

    return new runtime.JSONApiResponse(response, (jsonValue) =>
      EntryFromJSON(jsonValue)
    );
  }

  /**
   */
  async entryApiV2Retrieve(
    requestParameters: EntryApiV2RetrieveRequest,
    initOverrides?: RequestInit
  ): Promise<Entry> {
    const response = await this.entryApiV2RetrieveRaw(
      requestParameters,
      initOverrides
    );
    return await response.value();
  }
}