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
  UserRetrieveToken,
  UserRetrieveTokenFromJSON,
  UserRetrieveTokenFromJSONTyped,
  UserRetrieveTokenToJSON,
} from "./UserRetrieveToken";

/**
 *
 * @export
 * @interface UserRetrieve
 */
export interface UserRetrieve {
  /**
   *
   * @type {number}
   * @memberof UserRetrieve
   */
  readonly id: number;
  /**
   * Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.
   * @type {string}
   * @memberof UserRetrieve
   */
  username: string;
  /**
   *
   * @type {string}
   * @memberof UserRetrieve
   */
  email?: string;
  /**
   * Designates that this user has all permissions without explicitly assigning them.
   * @type {boolean}
   * @memberof UserRetrieve
   */
  isSuperuser?: boolean;
  /**
   *
   * @type {string}
   * @memberof UserRetrieve
   */
  readonly dateJoined: string;
  /**
   *
   * @type {UserRetrieveToken}
   * @memberof UserRetrieve
   */
  token: UserRetrieveToken | null;
}

export function UserRetrieveFromJSON(json: any): UserRetrieve {
  return UserRetrieveFromJSONTyped(json, false);
}

export function UserRetrieveFromJSONTyped(
  json: any,
  ignoreDiscriminator: boolean
): UserRetrieve {
  if (json === undefined || json === null) {
    return json;
  }
  return {
    id: json["id"],
    username: json["username"],
    email: !exists(json, "email") ? undefined : json["email"],
    isSuperuser: !exists(json, "is_superuser")
      ? undefined
      : json["is_superuser"],
    dateJoined: json["date_joined"],
    token: UserRetrieveTokenFromJSON(json["token"]),
  };
}

export function UserRetrieveToJSON(value?: UserRetrieve | null): any {
  if (value === undefined) {
    return undefined;
  }
  if (value === null) {
    return null;
  }
  return {
    username: value.username,
    email: value.email,
    is_superuser: value.isSuperuser,
    token: UserRetrieveTokenToJSON(value.token),
  };
}
