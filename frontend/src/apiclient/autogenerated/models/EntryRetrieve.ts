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
  Entity,
  EntityFromJSON,
  EntityFromJSONTyped,
  EntityToJSON,
} from "./Entity";
import {
  EntryRetrieveAttrs,
  EntryRetrieveAttrsFromJSON,
  EntryRetrieveAttrsFromJSONTyped,
  EntryRetrieveAttrsToJSON,
} from "./EntryRetrieveAttrs";

/**
 *
 * @export
 * @interface EntryRetrieve
 */
export interface EntryRetrieve {
  /**
   *
   * @type {number}
   * @memberof EntryRetrieve
   */
  readonly id: number;
  /**
   *
   * @type {string}
   * @memberof EntryRetrieve
   */
  name: string;
  /**
   *
   * @type {Entity}
   * @memberof EntryRetrieve
   */
  readonly schema: Entity | null;
  /**
   *
   * @type {boolean}
   * @memberof EntryRetrieve
   */
  readonly isActive: boolean;
  /**
   *
   * @type {Array<EntryRetrieveAttrs>}
   * @memberof EntryRetrieve
   */
  readonly attrs: Array<EntryRetrieveAttrs>;
}

export function EntryRetrieveFromJSON(json: any): EntryRetrieve {
  return EntryRetrieveFromJSONTyped(json, false);
}

export function EntryRetrieveFromJSONTyped(
  json: any,
  ignoreDiscriminator: boolean
): EntryRetrieve {
  if (json === undefined || json === null) {
    return json;
  }
  return {
    id: json["id"],
    name: json["name"],
    schema: EntityFromJSON(json["schema"]),
    isActive: json["is_active"],
    attrs: (json["attrs"] as Array<any>).map(EntryRetrieveAttrsFromJSON),
  };
}

export function EntryRetrieveToJSON(value?: EntryRetrieve | null): any {
  if (value === undefined) {
    return undefined;
  }
  if (value === null) {
    return null;
  }
  return {
    name: value.name,
  };
}