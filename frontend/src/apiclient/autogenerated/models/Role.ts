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
 * @interface Role
 */
export interface Role {
  /**
   *
   * @type {number}
   * @memberof Role
   */
  readonly id: number;
  /**
   *
   * @type {boolean}
   * @memberof Role
   */
  isActive?: boolean;
  /**
   *
   * @type {string}
   * @memberof Role
   */
  name: string;
  /**
   *
   * @type {string}
   * @memberof Role
   */
  description: string;
  /**
   *
   * @type {Array<number>}
   * @memberof Role
   */
  users: Array<number>;
  /**
   *
   * @type {Array<number>}
   * @memberof Role
   */
  groups: Array<number>;
  /**
   *
   * @type {Array<number>}
   * @memberof Role
   */
  adminUsers: Array<number>;
  /**
   *
   * @type {Array<number>}
   * @memberof Role
   */
  adminGroups: Array<number>;
}

export function RoleFromJSON(json: any): Role {
  return RoleFromJSONTyped(json, false);
}

export function RoleFromJSONTyped(
  json: any,
  ignoreDiscriminator: boolean
): Role {
  if (json === undefined || json === null) {
    return json;
  }
  return {
    id: json["id"],
    isActive: !exists(json, "is_active") ? undefined : json["is_active"],
    name: json["name"],
    description: json["description"],
    users: json["users"],
    groups: json["groups"],
    adminUsers: json["admin_users"],
    adminGroups: json["admin_groups"],
  };
}

export function RoleToJSON(value?: Role | null): any {
  if (value === undefined) {
    return undefined;
  }
  if (value === null) {
    return null;
  }
  return {
    is_active: value.isActive,
    name: value.name,
    description: value.description,
    users: value.users,
    groups: value.groups,
    admin_users: value.adminUsers,
    admin_groups: value.adminGroups,
  };
}
