function Get-AssetGuardPassphraseBytes {
    param([Parameter(Mandatory)][Security.SecureString]$Passphrase)
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Passphrase)
    try {
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
        if ($plain.Length -lt 16) { throw 'Backup passphrase must contain at least 16 characters.' }
        return [Text.Encoding]::UTF8.GetBytes($plain)
    } finally {
        if ($null -ne $plain) { $plain = $null }
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

function Get-AssetGuardBackupPassphrase {
    param(
        [Security.SecureString]$Passphrase,
        [string]$SavedPassphrasePath,
        [switch]$NonInteractive
    )
    if ($Passphrase) { return $Passphrase }
    if ($SavedPassphrasePath -and (Test-Path -LiteralPath $SavedPassphrasePath)) {
        $protected = Get-Content -LiteralPath $SavedPassphrasePath -Raw
        if (-not [string]::IsNullOrWhiteSpace($protected)) {
            # ConvertTo-SecureString uses Windows DPAPI here: only this Windows
            # user on this computer can recover the stored passphrase.
            return ConvertTo-SecureString $protected
        }
    }
    if ($env:ASSETGUARD_BACKUP_PASSPHRASE) {
        return ConvertTo-SecureString $env:ASSETGUARD_BACKUP_PASSPHRASE -AsPlainText -Force
    }
    if ($NonInteractive) { throw 'No DPAPI-protected backup passphrase is configured for this scheduled run.' }
    return Read-Host 'Backup passphrase (minimum 16 characters)' -AsSecureString
}

function Protect-AssetGuardBackup {
    param(
        [Parameter(Mandatory)][string]$InputFile,
        [Parameter(Mandatory)][string]$OutputFile,
        [Parameter(Mandatory)][Security.SecureString]$Passphrase
    )
    $magic = [Text.Encoding]::ASCII.GetBytes('AGBK1')
    $salt = [byte[]]::new(16)
    $nonce = [byte[]]::new(12)
    [Security.Cryptography.RandomNumberGenerator]::Fill($salt)
    [Security.Cryptography.RandomNumberGenerator]::Fill($nonce)
    $passphraseBytes = Get-AssetGuardPassphraseBytes $Passphrase
    $derive = [Security.Cryptography.Rfc2898DeriveBytes]::new($passphraseBytes, $salt, 210000, [Security.Cryptography.HashAlgorithmName]::SHA256)
    try {
        $key = $derive.GetBytes(32)
        $plaintext = [IO.File]::ReadAllBytes($InputFile)
        $ciphertext = [byte[]]::new($plaintext.Length)
        $tag = [byte[]]::new(16)
        $aes = [Security.Cryptography.AesGcm]::new($key, 16)
        try { $aes.Encrypt($nonce, $plaintext, $ciphertext, $tag, $magic) } finally { $aes.Dispose() }
        $output = [byte[]]::new($magic.Length + $salt.Length + $nonce.Length + $tag.Length + $ciphertext.Length)
        $offset = 0
        foreach ($part in @($magic, $salt, $nonce, $tag, $ciphertext)) {
            [Array]::Copy($part, 0, $output, $offset, $part.Length)
            $offset += $part.Length
        }
        [IO.File]::WriteAllBytes($OutputFile, $output)
    } finally {
        if ($key) { [Array]::Clear($key, 0, $key.Length) }
        if ($plaintext) { [Array]::Clear($plaintext, 0, $plaintext.Length) }
        if ($passphraseBytes) { [Array]::Clear($passphraseBytes, 0, $passphraseBytes.Length) }
        $derive.Dispose()
    }
}

function Unprotect-AssetGuardBackup {
    param(
        [Parameter(Mandatory)][string]$InputFile,
        [Parameter(Mandatory)][string]$OutputFile,
        [Parameter(Mandatory)][Security.SecureString]$Passphrase
    )
    $input = [IO.File]::ReadAllBytes($InputFile)
    $magic = [Text.Encoding]::ASCII.GetBytes('AGBK1')
    $validMagic = $input.Length -ge 49
    for ($index = 0; $validMagic -and $index -lt $magic.Length; $index++) {
        if ($input[$index] -ne $magic[$index]) { $validMagic = $false }
    }
    if (-not $validMagic) {
        throw 'The selected file is not an AssetGuard encrypted backup.'
    }
    [byte[]]$salt = $input[5..20]
    [byte[]]$nonce = $input[21..32]
    [byte[]]$tag = $input[33..48]
    [byte[]]$ciphertext = $input[49..($input.Length - 1)]
    $passphraseBytes = Get-AssetGuardPassphraseBytes $Passphrase
    $derive = [Security.Cryptography.Rfc2898DeriveBytes]::new($passphraseBytes, $salt, 210000, [Security.Cryptography.HashAlgorithmName]::SHA256)
    try {
        $key = $derive.GetBytes(32)
        $plaintext = [byte[]]::new($ciphertext.Length)
        $aes = [Security.Cryptography.AesGcm]::new($key, 16)
        try { $aes.Decrypt($nonce, $ciphertext, $tag, $plaintext, $magic) } finally { $aes.Dispose() }
        [IO.File]::WriteAllBytes($OutputFile, $plaintext)
    } finally {
        if ($key) { [Array]::Clear($key, 0, $key.Length) }
        if ($plaintext) { [Array]::Clear($plaintext, 0, $plaintext.Length) }
        if ($passphraseBytes) { [Array]::Clear($passphraseBytes, 0, $passphraseBytes.Length) }
        $derive.Dispose()
    }
}
