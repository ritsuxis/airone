import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import {
  Box,
  Checkbox,
  IconButton,
  Input,
  List,
  ListItem,
  Typography,
  TextField,
  Autocomplete,
} from "@mui/material";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { DesktopDatePicker } from "@mui/x-date-pickers/DesktopDatePicker";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import React, { FC, useEffect, useState } from "react";

import { EditableEntryAttrs } from "./EditableEntry";

import { aironeApiClientV2 } from "apiclient/AironeApiClientV2";
import {
  EntryRetrieveValueAsObject,
  EntryRetrieveValueAsObjectSchema,
} from "apiclient/autogenerated";
import { DjangoContext } from "utils/DjangoContext";

interface CommonProps {
  attrName: string;
  attrType: number;
  isMandatory: boolean;
  index?: number;
  handleChange: (attrName: string, attrType: number, valueInfo: any) => void;
}

const ElemString: FC<
  CommonProps & {
    attrValue: string;
    handleClickDeleteListItem?: (
      attrName: string,
      attrType: number,
      index?: number
    ) => void;
    handleClickAddListItem?: (
      attrName: string,
      attrType: number,
      index: number
    ) => void;
    multiline?: boolean;
    disabled?: boolean;
  }
> = ({
  attrName,
  attrValue,
  attrType,
  isMandatory,
  index,
  handleChange,
  handleClickDeleteListItem,
  handleClickAddListItem,
  multiline,
  disabled,
}) => {
  return (
    <Box display="flex" width="100%">
      <Input
        type="text"
        value={attrValue}
        onChange={(e) =>
          handleChange(attrName, attrType, {
            index: index,
            value: e.target.value,
          })
        }
        fullWidth
        multiline={multiline}
        error={isMandatory && attrValue === ""}
      />
      {index !== undefined && (
        <>
          <IconButton
            disabled={disabled}
            sx={{ mx: "20px" }}
            onClick={() => handleClickDeleteListItem(attrName, attrType, index)}
          >
            <DeleteOutlineIcon />
          </IconButton>
          <IconButton
            onClick={() => handleClickAddListItem(attrName, attrType, index)}
          >
            <AddIcon />
          </IconButton>
        </>
      )}
    </Box>
  );
};

const ElemBool: FC<CommonProps & { attrValue: boolean }> = ({
  attrName,
  attrValue,
  attrType,
  isMandatory,
  handleChange,
}) => {
  return (
    <Checkbox
      checked={attrValue}
      onChange={(e) =>
        handleChange(attrName, attrType, {
          index: undefined,
          checked: e.target.checked,
        })
      }
    />
  );
};

const ElemReferral: FC<
  CommonProps & {
    multiple?: boolean;
    attrValue:
      | EntryRetrieveValueAsObject
      | Array<EntryRetrieveValueAsObject>
      | EntryRetrieveValueAsObjectSchema
      | Array<EntryRetrieveValueAsObjectSchema>;
    schemaId?: number;
    disabled?: boolean;
    handleClickDeleteListItem?: (
      attrName: string,
      attrType: number,
      index?: number
    ) => void;
    handleClickAddListItem?: (
      attrName: string,
      attrType: number,
      index: number
    ) => void;
  }
> = ({
  multiple = false,
  attrName,
  attrValue,
  attrType,
  isMandatory,
  schemaId,
  index,
  disabled,
  handleChange,
  handleClickDeleteListItem,
  handleClickAddListItem,
}) => {
  const [keyword, setKeyword] = useState("");
  const [referrals, setReferrals] = useState([]);

  const djangoContext = DjangoContext.getInstance();

  useEffect(() => {
    (async () => {
      if (Number(attrType) & Number(djangoContext.attrTypeValue.object)) {
        // FIXME Implement and use API V2
        // TODO call it reactively to avoid loading API???
        const attrReferrals = await aironeApiClientV2.getEntryAttrReferrals(
          schemaId,
          keyword
        );
        const addReferrals = [];

        // Filter duplicate referrals.
        attrReferrals.forEach((result) => {
          if (!referrals.map((referral) => referral.id).includes(result.id)) {
            addReferrals.push(result);
          }
        });

        // Add current attr value to referrals.
        if (multiple) {
          (attrValue as Array<EntryRetrieveValueAsObject>).forEach((value) => {
            if (!referrals.map((referral) => referral.id).includes(value.id)) {
              addReferrals.push(value);
            }
          });
        } else {
          if (attrValue) {
            if (
              !referrals
                .map((referral) => referral.id)
                .includes((attrValue as EntryRetrieveValueAsObject).id)
            ) {
              addReferrals.push(attrValue);
            }
          }
        }
        setReferrals(referrals.concat(addReferrals));
      } else if (Number(attrType) & Number(djangoContext.attrTypeValue.group)) {
        const groups = await aironeApiClientV2.getGroups();
        const addReferrals = [];

        // Filter duplicate referrals.
        groups.forEach((result) => {
          if (!referrals.map((referral) => referral.id).includes(result.id)) {
            addReferrals.push(result);
          }
        });

        setReferrals(referrals.concat(addReferrals));
      } else if (Number(attrType) & Number(djangoContext.attrTypeValue.role)) {
        const roles = await aironeApiClientV2.getRoles();
        const addReferrals = [];

        // Filter duplicate referrals.
        roles.forEach((result) => {
          if (!referrals.map((referral) => referral.id).includes(result.id)) {
            addReferrals.push(result);
          }
        });

        setReferrals(referrals.concat(addReferrals));
      }
    })();
  }, [keyword]);

  return (
    <Box>
      <Typography variant="caption" color="rgba(0, 0, 0, 0.6)">
        {Number(attrType) & Number(djangoContext.attrTypeValue.object)
          ? "エントリを選択"
          : "グループを選択"}
      </Typography>
      <Box display="flex" alignItems="center">
        <Autocomplete
          sx={{ width: "280px" }}
          multiple={multiple}
          options={referrals}
          getOptionLabel={(option) => option.name}
          isOptionEqualToValue={(option, value) => option.id === value?.id}
          value={attrValue ?? null}
          onChange={(e, value) => {
            handleChange(attrName, attrType, {
              index: index,
              value: value,
            });
          }}
          onInputChange={(e, value) => {
            // To run only if the user changes
            if (e) {
              setKeyword(value);
            }
          }}
          renderInput={(params) => (
            <TextField
              {...params}
              error={
                isMandatory &&
                (multiple
                  ? (
                      attrValue as
                        | Array<EntryRetrieveValueAsObject>
                        | Array<EntryRetrieveValueAsObjectSchema>
                    )?.length === 0
                  : !attrValue)
              }
              size="small"
              placeholder={
                multiple &&
                (
                  attrValue as
                    | Array<EntryRetrieveValueAsObject>
                    | Array<EntryRetrieveValueAsObjectSchema>
                ).length
                  ? ""
                  : "-NOT SET-"
              }
            />
          )}
        />
        {index !== undefined && (
          <>
            <IconButton
              disabled={disabled}
              sx={{ mx: "20px" }}
              onClick={() =>
                handleClickDeleteListItem(attrName, attrType, index)
              }
            >
              <DeleteOutlineIcon />
            </IconButton>
            <IconButton
              onClick={() => handleClickAddListItem(attrName, attrType, index)}
            >
              <AddIcon />
            </IconButton>
          </>
        )}
      </Box>
    </Box>
  );
};

const ElemNamedObject: FC<
  CommonProps & {
    attrValue?: { [key: string]: EntryRetrieveValueAsObject };
    schemaId: number;
    disabled?: boolean;
    handleClickDeleteListItem?: (
      attrName: string,
      attrType: number,
      index?: number
    ) => void;
    handleClickAddListItem?: (
      attrName: string,
      attrType: number,
      index: number
    ) => void;
  }
> = ({
  attrName,
  attrValue,
  attrType,
  isMandatory,
  schemaId,
  index,
  disabled,
  handleChange,
  handleClickDeleteListItem,
  handleClickAddListItem,
}) => {
  const key = attrValue ? Object.keys(attrValue)[0] : "";
  return (
    <Box display="flex" alignItems="flex-end">
      <Box display="flex" flexDirection="column">
        <Typography variant="caption" color="rgba(0, 0, 0, 0.6)">
          name
        </Typography>
        <Box width="280px" mr="32px">
          <TextField
            variant="standard"
            value={key}
            onChange={(e) =>
              handleChange(attrName, attrType, {
                index: index,
                key: e.target.value,
                ...attrValue[key],
              })
            }
            error={isMandatory && !key && !attrValue[key]}
          />
        </Box>
      </Box>
      <ElemReferral
        schemaId={schemaId}
        attrName={attrName}
        attrValue={attrValue ? attrValue[key] : undefined}
        attrType={attrType}
        isMandatory={isMandatory && !key}
        index={index}
        disabled={disabled}
        handleChange={handleChange}
        handleClickDeleteListItem={handleClickDeleteListItem}
        handleClickAddListItem={handleClickAddListItem}
      />
    </Box>
  );
};

const ElemDate: FC<
  CommonProps & {
    attrValue: string;
    handleClickDeleteListItem: (attrName: string, index?: number) => void;
  }
> = ({ attrName, attrValue, attrType, isMandatory, handleChange }) => {
  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <DesktopDatePicker
        label="月日を選択"
        inputFormat="yyyy/MM/dd"
        value={attrValue ? attrValue : null}
        onChange={(date: Date) => {
          let settingDateValue = "";
          if (date !== null) {
            settingDateValue = `${date.getFullYear()}-${
              date.getMonth() + 1
            }-${date.getDate()}`;
          }

          handleChange(attrName, attrType, {
            value: settingDateValue,
          });
        }}
        renderInput={(params) => (
          <TextField {...params} error={isMandatory && attrValue === ""} />
        )}
      />
    </LocalizationProvider>
  );
};

interface Props {
  attrName: string;
  attrInfo: EditableEntryAttrs;
  handleChangeAttribute: (
    attrName: string,
    attrType: number,
    valueInfo: any
  ) => void;
  handleClickDeleteListItem: (
    attrName: string,
    attrType: number,
    index?: number
  ) => void;
  handleClickAddListItem: (
    attrName: string,
    attrType: number,
    index: number
  ) => void;
}

export const EditAttributeValue: FC<Props> = ({
  attrName,
  attrInfo,
  handleChangeAttribute,
  handleClickDeleteListItem,
  handleClickAddListItem,
}) => {
  const djangoContext = DjangoContext.getInstance();

  switch (attrInfo.type) {
    case djangoContext.attrTypeValue.string:
      return (
        <ElemString
          attrName={attrName}
          attrValue={attrInfo.value.asString}
          attrType={attrInfo.type}
          isMandatory={attrInfo.isMandatory}
          handleChange={handleChangeAttribute}
        />
      );

    case djangoContext.attrTypeValue.text:
      return (
        <ElemString
          attrName={attrName}
          attrValue={attrInfo.value.asString}
          attrType={attrInfo.type}
          isMandatory={attrInfo.isMandatory}
          handleChange={handleChangeAttribute}
          multiline
        />
      );

    case djangoContext.attrTypeValue.date:
      return (
        <ElemDate
          attrName={attrName}
          attrValue={attrInfo.value.asString}
          attrType={attrInfo.type}
          isMandatory={attrInfo.isMandatory}
          handleChange={handleChangeAttribute}
          handleClickDeleteListItem={handleClickDeleteListItem}
        />
      );

    case djangoContext.attrTypeValue.boolean:
      return (
        <ElemBool
          attrName={attrName}
          attrValue={attrInfo.value.asBoolean}
          attrType={attrInfo.type}
          isMandatory={attrInfo.isMandatory}
          handleChange={handleChangeAttribute}
        />
      );

    case djangoContext.attrTypeValue.object:
      return (
        <ElemReferral
          attrName={attrName}
          attrValue={attrInfo.value.asObject}
          attrType={attrInfo.type}
          isMandatory={attrInfo.isMandatory}
          schemaId={attrInfo.schema.id}
          handleChange={handleChangeAttribute}
        />
      );

    case djangoContext.attrTypeValue.group:
      return (
        <ElemReferral
          attrName={attrName}
          attrValue={attrInfo.value.asGroup}
          attrType={attrInfo.type}
          isMandatory={attrInfo.isMandatory}
          handleChange={handleChangeAttribute}
        />
      );

    case djangoContext.attrTypeValue.role:
      return (
        <ElemReferral
          attrName={attrName}
          attrValue={attrInfo.value.asRole}
          attrType={attrInfo.type}
          isMandatory={attrInfo.isMandatory}
          handleChange={handleChangeAttribute}
        />
      );

    case djangoContext.attrTypeValue.named_object:
      return (
        <ElemNamedObject
          attrName={attrName}
          attrValue={attrInfo.value.asNamedObject}
          attrType={attrInfo.type}
          isMandatory={attrInfo.isMandatory}
          schemaId={attrInfo.schema.id}
          handleChange={handleChangeAttribute}
        />
      );

    case djangoContext.attrTypeValue.array_object:
      return (
        <ElemReferral
          multiple={true}
          attrName={attrName}
          attrValue={attrInfo.value.asArrayObject}
          attrType={attrInfo.type}
          isMandatory={attrInfo.isMandatory}
          schemaId={attrInfo.schema.id}
          handleChange={handleChangeAttribute}
        />
      );

    case djangoContext.attrTypeValue.array_group:
      return (
        <ElemReferral
          multiple={true}
          attrName={attrName}
          attrValue={attrInfo.value.asArrayGroup}
          attrType={attrInfo.type}
          isMandatory={attrInfo.isMandatory}
          handleChange={handleChangeAttribute}
        />
      );

    case djangoContext.attrTypeValue.array_role:
      return (
        <ElemReferral
          multiple={true}
          attrName={attrName}
          attrValue={attrInfo.value.asArrayRole}
          attrType={attrInfo.type}
          isMandatory={attrInfo.isMandatory}
          handleChange={handleChangeAttribute}
        />
      );

    case djangoContext.attrTypeValue.array_string:
      return (
        <Box>
          <List>
            {attrInfo.value.asArrayString?.map((info, n) => (
              <ListItem key={n}>
                <ElemString
                  attrName={attrName}
                  attrValue={info}
                  attrType={attrInfo.type}
                  isMandatory={attrInfo.isMandatory}
                  index={n}
                  handleChange={handleChangeAttribute}
                  handleClickDeleteListItem={handleClickDeleteListItem}
                  handleClickAddListItem={handleClickAddListItem}
                  disabled={attrInfo.value.asArrayString?.length == 1}
                />
              </ListItem>
            ))}
          </List>
        </Box>
      );

    case djangoContext.attrTypeValue.array_named_object:
      return (
        <Box>
          <List>
            {attrInfo.value.asArrayNamedObject?.map((info, n) => (
              <ListItem key={n}>
                <ElemNamedObject
                  attrName={attrName}
                  attrValue={info}
                  attrType={attrInfo.type}
                  isMandatory={attrInfo.isMandatory}
                  schemaId={attrInfo.schema.id}
                  index={n}
                  disabled={attrInfo.value.asArrayNamedObject?.length == 1}
                  handleChange={handleChangeAttribute}
                  handleClickDeleteListItem={handleClickDeleteListItem}
                  handleClickAddListItem={handleClickAddListItem}
                />
              </ListItem>
            ))}
          </List>
        </Box>
      );

    case djangoContext.attrTypeValue.array_named_object_boolean:
      return (
        <Box>
          <List>
            {(
              attrInfo.value.asArrayNamedObject as {
                [key: string]: Pick<
                  EntryRetrieveValueAsObject,
                  "id" | "name" | "schema"
                > & {
                  boolean?: boolean;
                };
              }[]
            ).map((info, n) => {
              const key = info ? Object.keys(info)[0] : "";
              return (
                <ListItem key={n}>
                  <Box display="flex" alignItems="flex-end">
                    <Box display="flex" flexDirection="column">
                      <Typography variant="caption" color="rgba(0, 0, 0, 0.6)">
                        name
                      </Typography>
                      <Box width="260px">
                        <TextField
                          variant="standard"
                          value={key}
                          onChange={(e) =>
                            handleChangeAttribute(
                              attrName,
                              djangoContext.attrTypeValue.array_named_object,
                              {
                                index: n,
                                key: e.target.value,
                                ...info[key],
                              }
                            )
                          }
                          error={attrInfo.isMandatory && !key && !info[key]}
                        />
                      </Box>
                    </Box>
                    <Box
                      display="flex"
                      flexDirection="column"
                      width="60px"
                      mr="16px"
                    >
                      <Typography variant="caption" color="rgba(0, 0, 0, 0.6)">
                        使用不可
                      </Typography>
                      <Checkbox
                        checked={info[key]?.boolean ?? false}
                        onChange={(e) =>
                          handleChangeAttribute(attrName, attrInfo.type, {
                            index: n,
                            checked: e.target.checked,
                          })
                        }
                      />
                    </Box>
                    <ElemReferral
                      schemaId={attrInfo.schema.id}
                      attrName={attrName}
                      attrValue={info[key]?.id ? info[key] : undefined}
                      attrType={djangoContext.attrTypeValue.array_named_object}
                      isMandatory={attrInfo.isMandatory && !key}
                      index={n}
                      disabled={attrInfo.value.asArrayNamedObject?.length == 1}
                      handleChange={handleChangeAttribute}
                      handleClickDeleteListItem={handleClickDeleteListItem}
                      handleClickAddListItem={handleClickAddListItem}
                    />
                  </Box>
                </ListItem>
              );
            })}
          </List>
        </Box>
      );
  }
};
