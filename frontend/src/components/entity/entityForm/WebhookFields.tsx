import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import ModeEditOutlineOutlinedIcon from "@mui/icons-material/ModeEditOutlineOutlined";
import {
  Box,
  Button,
  Checkbox,
  IconButton,
  Input,
  Modal,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Theme,
  Typography,
} from "@mui/material";
import { makeStyles } from "@mui/styles";
import React, { FC, Fragment } from "react";

import { EntityUpdate } from "apiclient/autogenerated";

const useStyles = makeStyles<Theme>((theme) => ({
  button: {
    margin: theme.spacing(1),
  },
  modal: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  paper: {
    backgroundColor: theme.palette.background.paper,
    border: "2px solid #000",
    boxShadow: theme.shadows[5],
    padding: theme.spacing(2, 4, 3),
    width: "50%",
  },
  headerRow: {
    margin: "auto",
  },
  headerInput: {
    margin: "0px 5px 0px 0px",
  },
  tableBorderless: {
    "*": {
      borderBottom: "none",
    },
  },
}));

interface Props {
  entityInfo: EntityUpdate;
  setEntityInfo: (entityInfo: EntityUpdate) => void;
}

export const WebhookFields: FC<Props> = ({ entityInfo, setEntityInfo }) => {
  const classes = useStyles();

  const handleChangeWebhook = (index: number, key: string, value: any) => {
    entityInfo.webhooks[index][key] = value;
    setEntityInfo({ ...entityInfo });
  };

  const handleAppendWebhook = (nextTo) => {
    entityInfo.webhooks.splice(nextTo + 1, 0, {
      id: undefined,
      url: "",
      label: "",
      isEnabled: false,
      isVerified: false,
      headers: [],
      isDeleted: false,
    });
    setEntityInfo({ ...entityInfo });
  };

  const handleWebhookHeaderKey = (
    openModalIndex: number,
    headerIndex: number,
    value: any
  ) => {
    entityInfo.webhooks[openModalIndex].headers[headerIndex].headerKey = value;
    setEntityInfo({ ...entityInfo });
  };

  const handleWebhookHeaderValue = (
    openModalIndex: number,
    headerIndex: number,
    value: any
  ) => {
    entityInfo.webhooks[openModalIndex].headers[headerIndex].headerValue =
      value;
    setEntityInfo({ ...entityInfo });
  };

  const handleDeleteWebhook = (index: number) => {
    entityInfo.webhooks[index] = {
      ...entityInfo.webhooks[index],
      isDeleted: true,
    };
    setEntityInfo({ ...entityInfo });
  };

  const [openModalIndex, setOpenModalIndex] = React.useState(-1);
  const handleOpenModal = (webhookIndex) => {
    setOpenModalIndex(webhookIndex);
  };
  const handleCloseModal = () => setOpenModalIndex(-1);

  const handleAppendWebhookAdditionalHeader = (nextTo) => {
    entityInfo.webhooks[openModalIndex]?.headers.splice(nextTo + 1, 0, {
      headerKey: "",
      headerValue: "",
    });
    setEntityInfo({ ...entityInfo });
  };

  const handleDeleteWebhookAdditionalHeader = (index: number) => {
    entityInfo.webhooks[openModalIndex]?.headers.splice(index, 1);
    setEntityInfo({ ...entityInfo });
  };

  return (
    <Box>
      <Box my="32px">
        <Typography variant="h4" align="center">
          Webhook
        </Typography>
      </Box>

      <Table className="table table-bordered">
        <TableHead>
          <TableRow sx={{ backgroundColor: "#455A64" }}>
            <TableCell sx={{ color: "#FFFFFF" }}>URL</TableCell>
            <TableCell sx={{ color: "#FFFFFF" }}>ラベル</TableCell>
            <TableCell />
            <TableCell sx={{ color: "#FFFFFF" }}>URL有効化</TableCell>
            <TableCell sx={{ color: "#FFFFFF" }}>削除</TableCell>
            <TableCell sx={{ color: "#FFFFFF" }}>追加</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {entityInfo.webhooks.map((webhook, index) => (
            <TableRow key={index}>
              {/* TODO show isAvailable ??? */}
              {/* TODO update webhook */}
              {webhook.isDeleted !== true && (
                <Fragment key={index}>
                  <TableCell>
                    <Input
                      type="text"
                      value={webhook.url}
                      placeholder="URL"
                      sx={{ width: "100%" }}
                      onChange={(e) =>
                        handleChangeWebhook(index, "url", e.target.value)
                      }
                    />
                  </TableCell>
                  <TableCell>
                    <Input
                      type="text"
                      value={webhook.label}
                      placeholder="ラベル"
                      sx={{ width: "100%" }}
                      onChange={(e) =>
                        handleChangeWebhook(index, "label", e.target.value)
                      }
                    />
                  </TableCell>
                  <TableCell>
                    <IconButton onClick={() => handleOpenModal(index)}>
                      <ModeEditOutlineOutlinedIcon />
                    </IconButton>
                  </TableCell>
                  <TableCell>
                    <Checkbox
                      checked={webhook.isEnabled}
                      onChange={(e) =>
                        handleChangeWebhook(
                          index,
                          "isEnabled",
                          e.target.checked
                        )
                      }
                    />
                  </TableCell>
                  <TableCell>
                    <IconButton onClick={() => handleDeleteWebhook(index)}>
                      <DeleteOutlineIcon />
                    </IconButton>
                  </TableCell>
                  <TableCell>
                    <IconButton onClick={() => handleAppendWebhook(index)}>
                      <AddIcon />
                    </IconButton>
                  </TableCell>
                </Fragment>
              )}
            </TableRow>
          ))}
          {entityInfo.webhooks.filter((webhook) => !webhook.isDeleted)
            .length === 0 && (
            <TableRow>
              <TableCell></TableCell>
              <TableCell></TableCell>
              <TableCell></TableCell>
              <TableCell></TableCell>
              <TableCell></TableCell>
              <TableCell>
                <IconButton onClick={() => handleAppendWebhook(0)}>
                  <AddIcon />
                </IconButton>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
      <Modal
        aria-labelledby="transition-modal-title"
        aria-describedby="transition-modal-description"
        className={classes.modal}
        open={openModalIndex >= 0}
        onClose={handleCloseModal}
      >
        <Box className={classes.paper}>
          <Typography variant={"h6"}>AdditionalHeader (Optional)</Typography>
          <Typography variant={"caption"}>
            指定した endpoint URL
            に送るリクエストに付加するヘッダ情報を入力してください。
          </Typography>
          <Table className="table">
            <TableBody>
              {entityInfo.webhooks[openModalIndex]?.headers.length === 0 && (
                <TableRow>
                  <TableCell sx={{ p: "4px 8px 0px 0px", borderBottom: "0px" }}>
                    <TextField
                      label="Key"
                      variant="standard"
                      fullWidth={true}
                      disabled={true}
                      onClick={() => handleAppendWebhookAdditionalHeader(0)}
                    />
                  </TableCell>
                  <TableCell sx={{ p: "4px 8px 0px 0px", borderBottom: "0px" }}>
                    <TextField
                      label="Value"
                      variant="standard"
                      fullWidth={true}
                      disabled={true}
                      onClick={() => handleAppendWebhookAdditionalHeader(0)}
                    />
                  </TableCell>
                  <TableCell sx={{ borderBottom: "0px" }}>
                    <IconButton disabled={true}>
                      <DeleteOutlineIcon />
                    </IconButton>
                  </TableCell>
                  <TableCell sx={{ borderBottom: "0px" }}>
                    <IconButton
                      onClick={() => handleAppendWebhookAdditionalHeader(0)}
                    >
                      <AddIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              )}
              {entityInfo.webhooks[openModalIndex]?.headers.map(
                (header, index) => (
                  <TableRow key={index}>
                    <TableCell
                      sx={{ p: "4px 8px 0px 0px", borderBottom: "0px" }}
                    >
                      <TextField
                        label="Key"
                        variant="standard"
                        fullWidth={true}
                        value={header.headerKey}
                        onChange={(e) => {
                          handleWebhookHeaderKey(
                            openModalIndex,
                            index,
                            e.target.value
                          );
                        }}
                      />
                    </TableCell>
                    <TableCell
                      sx={{ p: "4px 8px 0px 0px", borderBottom: "0px" }}
                    >
                      <TextField
                        label="Value"
                        variant="standard"
                        fullWidth={true}
                        value={header.headerValue}
                        onChange={(e) => {
                          handleWebhookHeaderValue(
                            openModalIndex,
                            index,
                            e.target.value
                          );
                        }}
                      />
                    </TableCell>

                    <TableCell sx={{ borderBottom: "0px" }}>
                      <IconButton
                        onClick={() =>
                          handleDeleteWebhookAdditionalHeader(index)
                        }
                      >
                        <DeleteOutlineIcon />
                      </IconButton>
                    </TableCell>

                    <TableCell sx={{ borderBottom: "0px" }}>
                      <IconButton
                        onClick={() =>
                          handleAppendWebhookAdditionalHeader(index)
                        }
                      >
                        <AddIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                )
              )}
            </TableBody>
          </Table>

          <Box sx={{ width: "92%" }}>
            <Button onClick={handleCloseModal}>
              <Typography align="right">閉じる</Typography>
            </Button>
          </Box>
        </Box>
      </Modal>
    </Box>
  );
};
