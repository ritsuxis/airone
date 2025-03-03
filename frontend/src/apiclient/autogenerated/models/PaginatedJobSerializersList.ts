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
  JobSerializers,
  JobSerializersFromJSON,
  JobSerializersFromJSONTyped,
  JobSerializersToJSON,
} from "./JobSerializers";

/**
 *
 * @export
 * @interface PaginatedJobSerializersList
 */
export interface PaginatedJobSerializersList {
  /**
   *
   * @type {number}
   * @memberof PaginatedJobSerializersList
   */
  count?: number;
  /**
   *
   * @type {string}
   * @memberof PaginatedJobSerializersList
   */
  next?: string | null;
  /**
   *
   * @type {string}
   * @memberof PaginatedJobSerializersList
   */
  previous?: string | null;
  /**
   *
   * @type {Array<JobSerializers>}
   * @memberof PaginatedJobSerializersList
   */
  results?: Array<JobSerializers>;
}

export function PaginatedJobSerializersListFromJSON(
  json: any
): PaginatedJobSerializersList {
  return PaginatedJobSerializersListFromJSONTyped(json, false);
}

export function PaginatedJobSerializersListFromJSONTyped(
  json: any,
  ignoreDiscriminator: boolean
): PaginatedJobSerializersList {
  if (json === undefined || json === null) {
    return json;
  }
  return {
    count: !exists(json, "count") ? undefined : json["count"],
    next: !exists(json, "next") ? undefined : json["next"],
    previous: !exists(json, "previous") ? undefined : json["previous"],
    results: !exists(json, "results")
      ? undefined
      : (json["results"] as Array<any>).map(JobSerializersFromJSON),
  };
}

export function PaginatedJobSerializersListToJSON(
  value?: PaginatedJobSerializersList | null
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
        : (value.results as Array<any>).map(JobSerializersToJSON),
  };
}
