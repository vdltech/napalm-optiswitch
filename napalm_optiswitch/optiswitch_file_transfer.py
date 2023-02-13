"""
NAPALM Optiswitch File Transfer

Netmiko does not have have native MRV SCP support. This provides it.
"""
import logging
import os
import re
import socket

from netmiko.cisco_base_connection import BaseFileTransfer

logger = logging.getLogger(__name__)

# region Error Classes


class Error(Exception):
    pass


class ScpError(Error):
    """An error occurred while attempting a SCP copy."""


class ScpTimeoutError(ScpError):
    """A device failed to respond to a SCP command within the timeout."""


class ScpMinorError(ScpError):
    """A device reported a SCP minor error."""


class ScpMajorError(ScpError):
    """A device reported a SCP major error."""


class ScpProtocolError(ScpError):
    """An unexpected SCP error occurred."""


class ScpChannelError(ScpError):
    """An error occurred with the SCP channel."""


class ScpClosedError(ScpError):
    """A device closed the SCP connection."""


class SshConfigError(ScpError):
    """The configuration file is either missing or malformed."""


# endregion


class OptiSwitchFileTransfer(BaseFileTransfer):
    def __init__(
        self,
        ssh_conn,
        source_file,
        dest_file,
        file_system="/usr/local/etc/sys",
        direction="put",
        timeout=30,
    ):
        # call our parent
        super(OptiSwitchFileTransfer, self).__init__(
            ssh_conn, source_file, dest_file, file_system, direction
        )

        self._timeout = timeout
        self._source_size = 0
        self.establish_scp_conn()

    def check_file_exists(self, remote_cmd=""):
        """Check if the dest_file already exists on the file system (return boolean)."""
        if self.direction == "put":
            if not remote_cmd:
                remote_cmd = f"dir conf"
            remote_out = self.ssh_ctl_chan._send_command_str(remote_cmd)
            search_string = r".*{0}\n".format(self.dest_file)
            if re.search(search_string, remote_out, flags=re.DOTALL):
                return True
            else:
                return False
        elif self.direction == "get":
            return os.path.exists(self.dest_file)
        else:
            raise ValueError("Unexpected value for self.direction")

    def remote_file_size(self, remote_cmd="", remote_file=None):
        """Get the file size of the remote file."""
        if remote_file is None:
            if self.direction == "put":
                remote_file = self.dest_file
            elif self.direction == "get":
                remote_file = self.source_file
        if not remote_cmd:
            remote_cmd = "dir conf"
        remote_out = self.ssh_ctl_chan.send_command(remote_cmd)

        # remote output format: -rwxrwxrwx 1 root admin 4358 Feb 7 07:59 System.conf
        search_string = "(\d+) \S+\s+\d+ \d+:\d+ {0}\n".format(self.dest_file)
        search_result = re.search(search_string, remote_out, flags=re.DOTALL)
        if search_result:
            return int(search_result.group(1))
        else:
            raise IOError("Unable to find file on remote system")

    def remote_space_available(self, search_pattern=r"\D+\s+\d+\s+\d+\s+(\d+)\s+\d+%"):
        """
        Return space available on remote device.

        Example Output:
        $ df /usr/local/etc/sys/
        Filesystem           1k-blocks      Used Available Use% Mounted on
        none                     10240       292      9948   3% /usr/local/etc
        :param search_pattern:
        :return:
        """

        remote_output = self._run_linux_command("df -k {} | tail -n 1".format(self.file_system))
        match = re.search(search_pattern, remote_output)
        return int(match.group(1)) * 1024 if match else -1

    def verify_space_available(self, search_pattern=r"\D+\s+\d+\s+\d+\s+(\d+)\s+\d+%"):
        """Verify sufficient space is available on destination file system (return boolean)."""
        space_avail = 0
        if self.direction == "put":
            space_avail = self.remote_space_available(search_pattern=search_pattern)
        elif self.direction == "get":
            space_avail = self.local_space_available()

        if space_avail > self.file_size:
            return True
        return False

    def remote_md5(self, base_cmd="md5sum", remote_file=None):
        if not remote_file:
            remote_file = self.dest_file
        remote_file_path = "{}/{}".format(self.file_system, remote_file)
        output = self._run_linux_command("md5sum {}".format(remote_file_path))
        return output.split()[0]

    def _run_linux_command(self, command):
        self.ssh_ctl_chan.send_command("linux", expect_string=r"\$")
        remote_output = self.ssh_ctl_chan.send_command(command, expect_string=r"\$")
        self.ssh_ctl_chan.send_command("exit", expect_string=r"#")
        return remote_output
