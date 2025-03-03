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
  EntityDetailAttrs,
  EntityDetailAttrsFromJSON,
  EntityDetailAttrsFromJSONTyped,
  EntityDetailAttrsToJSON,
} from "./EntityDetailAttrs";
import {
  Webhook,
  WebhookFromJSON,
  WebhookFromJSONTyped,
  WebhookToJSON,
} from "./Webhook";

/**
 *
 * @export
 * @interface EntityDetail
 */
export interface EntityDetail {
  /**
   *
   * @type {number}
   * @memberof EntityDetail
   */
  readonly id: number;
  /**
   *
   * @type {string}
   * @memberof EntityDetail
   */
  name: string;
  /**
   *
   * @type {string}
   * @memberof EntityDetail
   */
  note?: string;
  /**
   *
   * @type {number}
   * @memberof EntityDetail
   */
  status?: number;
  /**
   *
   * @type {boolean}
   * @memberof EntityDetail
   */
  readonly isToplevel: boolean;
  /**
   *
   * @type {Array<EntityDetailAttrs>}
   * @memberof EntityDetail
   */
  readonly attrs: Array<EntityDetailAttrs>;
  /**
   *
   * @type {Array<Webhook>}
   * @memberof EntityDetail
   */
  webhooks: Array<Webhook>;
  /**
   *
   * @type {boolean}
   * @memberof EntityDetail
   */
  isPublic?: boolean;
}

export function EntityDetailFromJSON(json: any): EntityDetail {
  return EntityDetailFromJSONTyped(json, false);
}

export function EntityDetailFromJSONTyped(
  json: any,
  ignoreDiscriminator: boolean
): EntityDetail {
  if (json === undefined || json === null) {
    return json;
  }
  return {
    id: json["id"],
    name: json["name"],
    note: !exists(json, "note") ? undefined : json["note"],
    status: !exists(json, "status") ? undefined : json["status"],
    isToplevel: json["is_toplevel"],
    attrs: (json["attrs"] as Array<any>).map(EntityDetailAttrsFromJSON),
    webhooks: (json["webhooks"] as Array<any>).map(WebhookFromJSON),
    isPublic: !exists(json, "is_public") ? undefined : json["is_public"],
  };
}

export function EntityDetailToJSON(value?: EntityDetail | null): any {
  if (value === undefined) {
    return undefined;
  }
  if (value === null) {
    return null;
  }
  return {
    name: value.name,
    note: value.note,
    status: value.status,
    webhooks: (value.webhooks as Array<any>).map(WebhookToJSON),
    is_public: value.isPublic,
  };
}
