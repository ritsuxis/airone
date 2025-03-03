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

import { exists, mapValues } from "../runtime";
import {
  GetEntrySimple,
  GetEntrySimpleFromJSON,
  GetEntrySimpleFromJSONTyped,
  GetEntrySimpleToJSON,
} from "./GetEntrySimple";

/**
 *
 * @export
 * @interface PaginatedGetEntrySimpleList
 */
export interface PaginatedGetEntrySimpleList {
  /**
   *
   * @type {number}
   * @memberof PaginatedGetEntrySimpleList
   */
  count?: number;
  /**
   *
   * @type {string}
   * @memberof PaginatedGetEntrySimpleList
   */
  next?: string | null;
  /**
   *
   * @type {string}
   * @memberof PaginatedGetEntrySimpleList
   */
  previous?: string | null;
  /**
   *
   * @type {Array<GetEntrySimple>}
   * @memberof PaginatedGetEntrySimpleList
   */
  results?: Array<GetEntrySimple>;
}

export function PaginatedGetEntrySimpleListFromJSON(
  json: any
): PaginatedGetEntrySimpleList {
  return PaginatedGetEntrySimpleListFromJSONTyped(json, false);
}

export function PaginatedGetEntrySimpleListFromJSONTyped(
  json: any,
  ignoreDiscriminator: boolean
): PaginatedGetEntrySimpleList {
  if (json === undefined || json === null) {
    return json;
  }
  return {
    count: !exists(json, "count") ? undefined : json["count"],
    next: !exists(json, "next") ? undefined : json["next"],
    previous: !exists(json, "previous") ? undefined : json["previous"],
    results: !exists(json, "results")
      ? undefined
      : (json["results"] as Array<any>).map(GetEntrySimpleFromJSON),
  };
}

export function PaginatedGetEntrySimpleListToJSON(
  value?: PaginatedGetEntrySimpleList | null
): any {
  if (value === undefined) {
    return undefined;
  }
  if (value === null) {
    return null;
  }
  return {
    count: value.count,
    next: value.next,
    previous: value.previous,
    results:
      value.results === undefined
        ? undefined
        : (value.results as Array<any>).map(GetEntrySimpleToJSON),
  };
}
