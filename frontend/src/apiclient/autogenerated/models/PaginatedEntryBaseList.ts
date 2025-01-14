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
  EntryBase,
  EntryBaseFromJSON,
  EntryBaseFromJSONTyped,
  EntryBaseToJSON,
} from "./EntryBase";

/**
 *
 * @export
 * @interface PaginatedEntryBaseList
 */
export interface PaginatedEntryBaseList {
  /**
   *
   * @type {number}
   * @memberof PaginatedEntryBaseList
   */
  count?: number;
  /**
   *
   * @type {string}
   * @memberof PaginatedEntryBaseList
   */
  next?: string | null;
  /**
   *
   * @type {string}
   * @memberof PaginatedEntryBaseList
   */
  previous?: string | null;
  /**
   *
   * @type {Array<EntryBase>}
   * @memberof PaginatedEntryBaseList
   */
  results?: Array<EntryBase>;
}

export function PaginatedEntryBaseListFromJSON(
  json: any
): PaginatedEntryBaseList {
  return PaginatedEntryBaseListFromJSONTyped(json, false);
}

export function PaginatedEntryBaseListFromJSONTyped(
  json: any,
  ignoreDiscriminator: boolean
): PaginatedEntryBaseList {
  if (json === undefined || json === null) {
    return json;
  }
  return {
    count: !exists(json, "count") ? undefined : json["count"],
    next: !exists(json, "next") ? undefined : json["next"],
    previous: !exists(json, "previous") ? undefined : json["previous"],
    results: !exists(json, "results")
      ? undefined
      : (json["results"] as Array<any>).map(EntryBaseFromJSON),
  };
}

export function PaginatedEntryBaseListToJSON(
  value?: PaginatedEntryBaseList | null
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
        : (value.results as Array<any>).map(EntryBaseToJSON),
  };
}
