import { Box, Typography } from "@mui/material";
import React, { FC } from "react";
import { Link } from "react-router-dom";
import { useAsync } from "react-use";

import { aironeApiClientV2 } from "../apiclient/AironeApiClientV2";
import { useTypedParams } from "../hooks/useTypedParams";

import { topPath, usersPath } from "Routes";
import { AironeBreadcrumbs } from "components/common/AironeBreadcrumbs";
import { Loading } from "components/common/Loading";
import { UserForm } from "components/user/UserForm";

export const EditUserPage: FC = () => {
  const { userId } = useTypedParams<{ userId: number }>();

  const user = useAsync(async () => {
    if (userId) {
      return await aironeApiClientV2.getUser(userId);
    }
  });

  return (
    <Box>
      <AironeBreadcrumbs>
        <Typography component={Link} to={topPath()}>
          Top
        </Typography>
        <Typography component={Link} to={usersPath()}>
          ユーザ管理
        </Typography>
        <Typography color="textPrimary">ユーザ編集</Typography>
      </AironeBreadcrumbs>

      {user.loading ? <Loading /> : <UserForm user={user.value} />}
    </Box>
  );
};
