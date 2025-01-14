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
  EntryRetrieveValueAsObjectSchema,
  EntryRetrieveValueAsObjectSchemaFromJSON,
  EntryRetrieveValueAsObjectSchemaFromJSONTyped,
  EntryRetrieveValueAsObjectSchemaToJSON,
} from "./EntryRetrieveValueAsObjectSchema";

/**
 *
 * @export
 * @interface EntryRetrieveValueAsObject
 */
export interface EntryRetrieveValueAsObject {
  /**
   *
   * @type {number}
   * @memberof EntryRetrieveValueAsObject
   */
  id?: number;
  /**
   *
   * @type {string}
   * @memberof EntryRetrieveValueAsObject
   */
  name?: string;
  /**
   *
   * @type {EntryRetrieveValueAsObjectSchema}
   * @memberof EntryRetrieveValueAsObject
   */
  schema?: EntryRetrieveValueAsObjectSchema;
}

export function EntryRetrieveValueAsObjectFromJSON(
  json: any
): EntryRetrieveValueAsObject {
  return EntryRetrieveValueAsObjectFromJSONTyped(json, false);
}

export function EntryRetrieveValueAsObjectFromJSONTyped(
  json: any,
  ignoreDiscriminator: boolean
): EntryRetrieveValueAsObject {
  if (json === undefined || json === null) {
    return json;
  }
  return {
    id: !exists(json, "id") ? undefined : json["id"],
    name: !exists(json, "name") ? undefined : json["name"],
    schema: !exists(json, "schema")
      ? undefined
      : EntryRetrieveValueAsObjectSchemaFromJSON(json["schema"]),
  };
}

export function EntryRetrieveValueAsObjectToJSON(
  value?: EntryRetrieveValueAsObject | null
): any {
  if (value === undefined) {
    return undefined;
  }
  if (value === null) {
    return null;
  }
  return {
    id: value.id,
    name: value.name,
    schema: EntryRetrieveValueAsObjectSchemaToJSON(value.schema),
  };
}
