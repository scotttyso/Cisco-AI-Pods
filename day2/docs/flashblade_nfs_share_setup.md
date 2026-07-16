# Pure Storage FlashBlade NFS Share Setup

This guide provides step-by-step instructions to create an NFS share on a Pure Storage FlashBlade array.

## Prerequisites

- Access to Pure Storage FlashBlade management interface
- Administrative credentials
- Network planning (CIDR ranges, export sizing)

## Step 1: Create NFS Export Policy

### Navigate to Policies

1. In the FlashBlade management console, navigate to **Policies** > **NFS Export Policies**
2. Click the **+** button to create a new policy

### Configure Policy

1. Give the policy a descriptive **Name** (e.g., `ai-pods-export-policy`)
2. Click **Create**

### Add Export Rule

1. Under the newly created policy, click **+** to add a new Export Rule

### Configure Export Rule

Set the following parameters:

- **Client**: Enter the client subnet (e.g., `198.18.1.0/24`)
- **Permission**: Check **Read-Write**
- **Security Protocol**: Check **sys**
- **Access**: Select **no-squash**
- Click **Add** to confirm

## Step 2: Create NFS File System

### Navigate to File Systems

1. In the FlashBlade management console, navigate to **Storage** > **File Systems**
2. Click the **+** button to create a new file system

### Configure File System

1. Give the file system a descriptive **Name** (e.g., `ai-pods-nfs-storage`)
2. Set the **Size** in bytes:
   - Example: `20G` for 20 gigabytes
   - Example: `1T` for 1 terabyte
3. Ensure **NFSv3** is selected as the protocol
4. Select your **Export Policy**
5. Click **Create**

## Verification

To verify the NFS share is accessible:

```bash
# List available NFS exports
showmount -e <flashblade-ip>

# Mount the NFS share (Linux/Unix)
sudo mount -t nfs <flashblade-ip>:/<filesystem-name> /mnt/nfs-share

# Verify mount
df -h /mnt/nfs-share
```

## Example Configuration

**Policy Name**: `ai-pods-export-policy`  
**Export Rule**: 
- Client: `198.18.1.0/24`
- Permission: Read-Write
- Security: sys
- Access: no-squash

**File System**:
- Name: `ai-pods-nfs-storage`
- Size: `1T`
- Protocol: NFSv3

## Troubleshooting

### Cannot Access NFS Share

- Verify the client IP is within the configured subnet range
- Check FlashBlade network connectivity
- Ensure firewall rules allow NFS traffic (ports 111, 2049)
- Verify the export policy is attached to the file system

### Permission Denied Errors

- Confirm the export rule has **Read-Write** permission enabled
- Verify **no-squash** access is configured
- Check client mount options match the policy settings

## Additional Resources

- [Pure Storage FlashBlade Documentation](https://purestorage.com)
- [NFS Best Practices](https://support.purestorage.com)
