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
/**
 *
 * @export
 * @interface EntityAttrCreate
 */
export interface EntityAttrCreate {
  /**
   *
   * @type {string}
   * @memberof EntityAttrCreate
   */
  name: string;
  /**
   *
   * @type {number}
   * @memberof EntityAttrCreate
   */
  type: number;
  /**
   *
   * @type {boolean}
   * @memberof EntityAttrCreate
   */
  isMandatory?: boolean;
  /**
   *
   * @type {Array<number>}
   * @memberof EntityAttrCreate
   */
  referral?: Array<number>;
  /**
   *
   * @type {number}
   * @memberof EntityAttrCreate
   */
  index?: number;
  /**
   *
   * @type {boolean}
   * @memberof EntityAttrCreate
   */
  isSummarized?: boolean;
  /**
   *
   * @type {boolean}
   * @memberof EntityAttrCreate
   */
  isDeleteInChain?: boolean;
}

export function EntityAttrCreateFromJSON(json: any): EntityAttrCreate {
  return EntityAttrCreateFromJSONTyped(json, false);
}

export function EntityAttrCreateFromJSONTyped(
  json: any,
  ignoreDiscriminator: boolean
): EntityAttrCreate {
  if (json === undefined || json === null) {
    return json;
  }
  return {
    name: json["name"],
    type: json["type"],
    isMandatory: !exists(json, "is_mandatory")
      ? undefined
      : json["is_mandatory"],
    referral: !exists(json, "referral") ? undefined : json["referral"],
    index: !exists(json, "index") ? undefined : json["index"],
    isSummarized: !exists(json, "is_summarized")
      ? undefined
      : json["is_summarized"],
    isDeleteInChain: !exists(json, "is_delete_in_chain")
      ? undefined
      : json["is_delete_in_chain"],
  };
}

export function EntityAttrCreateToJSON(value?: EntityAttrCreate | null): any {
  if (value === undefined) {
    return undefined;
  }
  if (value === null) {
    return null;
  }
  return {
    name: value.name,
    type: value.type,
    is_mandatory: value.isMandatory,
    referral: value.referral,
    index: value.index,
    is_summarized: value.isSummarized,
    is_delete_in_chain: value.isDeleteInChain,
  };
}
