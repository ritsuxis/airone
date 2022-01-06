import CheckIcon from "@mui/icons-material/Check";
import CloseIcon from "@mui/icons-material/Close";
import DeleteIcon from "@mui/icons-material/Delete";
import {
  Alert,
  Avatar,
  Box,
  Button,
  Checkbox,
  FormControl,
  FormControlLabel,
  FormGroup,
  List,
  ListItem,
  ListItemAvatar,
  ListItemSecondaryAction,
  ListItemText,
  Modal,
  TextField,
  Theme,
} from "@mui/material";
import { makeStyles } from "@mui/styles";
import React, { FC } from "react";
import { useAsync, useToggle } from "react-use";

import {
  deleteWebhook,
  getWebhooks,
  setWebhook,
} from "../../utils/AironeAPIClient";
import { DeleteButton } from "../common/DeleteButton";

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
    width: "80%",
  },
}));

interface Props {
  entityId: number;
}

export const WebhookForm: FC<Props> = ({ entityId }) => {
  const classes = useStyles();

  const [isUpdated, toggleIsUpdated] = useToggle(false);
  const webhooks = useAsync(async () => {
    return getWebhooks(entityId).then((resp) => resp.json());
  }, [isUpdated]);

  const [open, setOpen] = React.useState(false);
  const [webhook_headers, setWebhookHeaders] = React.useState([]);
  const [is_available, setAvailability] = React.useState(false);
  const [webhook_url, setWebhookURL] = React.useState("");
  const [webhook_label, setWebhookLabel] = React.useState("");
  const [alert_msg, setAlertMsg] = React.useState("");
  const [webhookId, setWebhookId] = React.useState(0);

  const handleOpenModal = (event, item?: any) => {
    console.log(item);
    setOpen(true);
    setWebhookURL(item ? item.url : "");
    setWebhookLabel(item ? item.label : "");
    const headers = item
      ? Object.keys(item.headers).map((key) => {
          const value = item.headers[key];
          return {
            key: key,
            value: value,
          };
        })
      : [];
    setWebhookHeaders(headers);
    setAlertMsg("");
    setAvailability(item ? item.is_enabled : false);
    setWebhookId(item ? item.id : 0);
  };

  const handleCloseModal = () => {
    setOpen(false);
  };

  const handleRegisterWebhook = () => {
    // This parameter is invalid on purpose
    const request_parameter = {
      id: webhookId > 0 ? webhookId : undefined,
      label: webhook_label,
      webhook_url: webhook_url,
      request_headers: webhook_headers,
      is_enabled: is_available,
    };

    setWebhook(entityId, request_parameter).then((resp) => {
      if (resp.ok) {
        handleCloseModal();

        toggleIsUpdated();
      } else {
        setAlertMsg(resp.statusText);
      }
    });
  };

  const handleDeleteWebhook = (e, webhookId) => {
    deleteWebhook(webhookId).then(() => {
      toggleIsUpdated();
    });
  };

  const handleAddHeaderElem = () => {
    setWebhookHeaders([...webhook_headers, { key: "", value: "" }]);
  };

  const handleDeleteHeaderElem = (e, index) => {
    webhook_headers.splice(index, 1);
    setWebhookHeaders([...webhook_headers]);
  };

  const handleChangeHeaderKey = (e, index) => {
    webhook_headers[index]["key"] = e.target.value;
    setWebhookHeaders([...webhook_headers]);
  };

  const handleChangeHeaderValue = (e, index) => {
    webhook_headers[index]["value"] = e.target.value;
    setWebhookHeaders([...webhook_headers]);
  };

  const handleChangeAvailability = (e) => {
    setAvailability(e.target.checked);
  };

  const handleChangeWebhookURL = (e) => {
    setWebhookURL(e.target.value);
  };

  const handleChangeWebhookLabel = (e) => {
    setWebhookLabel(e.target.value);
  };

  return (
    <Box>
      <Button
        className={classes.button}
        onClick={handleOpenModal}
        type="submit"
        variant="contained"
        color="secondary"
      >
        Add Webhook
      </Button>

      {/*This is testing display*/}
      <List>
        {!webhooks.loading &&
          webhooks.value.map((item) => (
            <ListItem
              key={item.id}
              button
              onClick={(e) => handleOpenModal(e, item)}
            >
              <ListItemAvatar>
                <Avatar>
                  {item.is_verified ? <CheckIcon /> : <CloseIcon />}
                </Avatar>
              </ListItemAvatar>
              <ListItemText primary={item.url} secondary={item.label} />
              <ListItemSecondaryAction>
                {/* TODO replace it with non-button element */}
                <DeleteButton
                  startIcon={<DeleteIcon />}
                  handleDelete={(e) => handleDeleteWebhook(e, item.id)}
                />
              </ListItemSecondaryAction>
            </ListItem>
          ))}
      </List>

      <Modal
        aria-labelledby="transition-modal-title"
        aria-describedby="transition-modal-description"
        className={classes.modal}
        open={open}
        onClose={handleCloseModal}
      >
        <Box className={classes.paper}>
          <Box hidden={alert_msg === ""}>
            <Alert severity="warning">{alert_msg}</Alert>
          </Box>

          <h2 id="transition-modal-title">Webhook の登録</h2>
          <form className={classes.root} noValidate autoComplete="off">
            <Box>
              <TextField
                id="input-webhoook-url"
                label="Webhook URL"
                variant="outlined"
                value={webhook_url}
                onChange={handleChangeWebhookURL}
              />
            </Box>

            <Box>
              <TextField
                id="input-label"
                label="Label (Optional)"
                variant="outlined"
                value={webhook_label}
                onChange={handleChangeWebhookLabel}
              />
            </Box>
            <Box>
              <FormControl component="fieldset">
                <FormGroup aria-label="position" row>
                  <FormControlLabel
                    value="end"
                    control={
                      <Checkbox
                        color="primary"
                        onChange={handleChangeAvailability}
                        checked={is_available}
                      />
                    }
                    label="有効化"
                    labelPlacement="end"
                  />
                </FormGroup>
              </FormControl>
            </Box>

            <Box>
              <h2>Additional Headers (Optional)</h2>
            </Box>

            <Box className={classes.webhook_headers_container}>
              {webhook_headers.map((data, index) => (
                <Box key={index}>
                  <TextField
                    label="Header Key {index}"
                    variant="outlined"
                    onChange={(e) => handleChangeHeaderKey(e, index)}
                    value={data["key"]}
                  />
                  <TextField
                    label={`Header Value ${index}`}
                    variant="outlined"
                    onChange={(e) => handleChangeHeaderValue(e, index)}
                    value={data["value"]}
                  />
                  <Button
                    variant="contained"
                    color="secondary"
                    onClick={(e) => handleDeleteHeaderElem(e, index)}
                  >
                    -
                  </Button>
                </Box>
              ))}
            </Box>

            <Box>
              ここで入力した情報を、リクエストのヘッダ情報に付加します。必要に応じてご入力ください。
            </Box>
            <Box>
              <Button
                variant="contained"
                color="primary"
                onClick={handleAddHeaderElem}
              >
                +
              </Button>
            </Box>
          </form>

          <Button
            className={classes.button}
            onClick={handleRegisterWebhook}
            type="submit"
            variant="contained"
            color="secondary"
          >
            {webhookId === 0 ? "REGISTER" : "UPDATE"}
          </Button>
        </Box>
      </Modal>
    </Box>
  );
};