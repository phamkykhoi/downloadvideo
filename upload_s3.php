#!/usr/bin/env php
<?php
/**
 * Upload các folder bài học trong downloads/ lên Vietnix S3 (public-read).
 * Không cần Composer — chỉ PHP + curl.
 *
 * Usage:
 *   php upload_s3.php
 *   php upload_s3.php --dry-run
 *   php upload_s3.php --downloads downloads
 *   php upload_s3.php --folder Numbers_8s-2m55s
 *   php upload_s3.php --folder Numbers_8s-2m55s --folder Shapes_11s-2m35s
 *   php upload_s3.php --folder Animals_6s-4m20s --only-hls
 */

declare(strict_types=1);

const CONTENT_TYPES = [
    'm3u8' => 'application/vnd.apple.mpegurl',
    'm4s'  => 'video/iso.segment',
    'ts'   => 'video/mp2t',
    'mp4'  => 'video/mp4',
    'mp3'  => 'audio/mpeg',
];

function loadEnv(string $path): array
{
    if (!is_file($path)) {
        fwrite(STDERR, "Thiếu file .env — copy từ .env.example\n");
        exit(1);
    }

    $env = [];
    foreach (file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
        $line = trim($line);
        if ($line === '' || str_starts_with($line, '#')) {
            continue;
        }
        [$key, $value] = array_pad(explode('=', $line, 2), 2, '');
        $env[trim($key)] = trim($value);
    }

    $required = [
        'VIETNIX_S3_ACCESS_KEY',
        'VIETNIX_S3_SECRET_KEY',
        'VIETNIX_S3_ENDPOINT',
        'VIETNIX_S3_BUCKET',
        'VIETNIX_S3_PUBLIC_URL',
        'VIETNIX_S3_BASE_KEY',
    ];

    foreach ($required as $key) {
        if (empty($env[$key])) {
            fwrite(STDERR, "Thiếu biến môi trường: $key\n");
            exit(1);
        }
    }

    $env['VIETNIX_S3_REGION'] = $env['VIETNIX_S3_REGION'] ?? 'auto';

    return $env;
}

function contentType(string $filename): string
{
    $ext = strtolower(pathinfo($filename, PATHINFO_EXTENSION));
    return CONTENT_TYPES[$ext] ?? 'application/octet-stream';
}

function encodeS3Key(string $key): string
{
    return implode('/', array_map('rawurlencode', explode('/', $key)));
}

function signingKey(string $secret, string $dateStamp, string $region, string $service): string
{
    $kDate = hash_hmac('sha256', $dateStamp, 'AWS4' . $secret, true);
    $kRegion = hash_hmac('sha256', $region, $kDate, true);
    $kService = hash_hmac('sha256', $service, $kRegion, true);

    return hash_hmac('sha256', 'aws4_request', $kService, true);
}

function signPutRequest(array $cfg, string $key, string $contentType, bool $useAcl): array
{
    $endpoint = rtrim($cfg['VIETNIX_S3_ENDPOINT'], '/');
    $bucket = $cfg['VIETNIX_S3_BUCKET'];
    $region = $cfg['VIETNIX_S3_REGION'] === 'auto' ? 'us-east-1' : $cfg['VIETNIX_S3_REGION'];
    $host = parse_url($endpoint, PHP_URL_HOST);

    $amzDate = gmdate('Ymd\THis\Z');
    $dateStamp = gmdate('Ymd');
    $canonicalUri = '/' . $bucket . '/' . encodeS3Key($key);

    $headers = [
        'content-type' => $contentType,
        'host' => $host,
        'x-amz-content-sha256' => 'UNSIGNED-PAYLOAD',
        'x-amz-date' => $amzDate,
    ];
    if ($useAcl) {
        $headers['x-amz-acl'] = 'public-read';
    }
    ksort($headers);

    $canonicalHeaders = '';
    $signedHeaderNames = [];
    foreach ($headers as $name => $value) {
        $canonicalHeaders .= $name . ':' . trim($value) . "\n";
        $signedHeaderNames[] = $name;
    }
    $signedHeaders = implode(';', $signedHeaderNames);

    $canonicalRequest = implode("\n", [
        'PUT',
        $canonicalUri,
        '',
        $canonicalHeaders,
        $signedHeaders,
        'UNSIGNED-PAYLOAD',
    ]);

    $credentialScope = "$dateStamp/$region/s3/aws4_request";
    $stringToSign = implode("\n", [
        'AWS4-HMAC-SHA256',
        $amzDate,
        $credentialScope,
        hash('sha256', $canonicalRequest),
    ]);

    $signature = hash_hmac(
        'sha256',
        $stringToSign,
        signingKey($cfg['VIETNIX_S3_SECRET_KEY'], $dateStamp, $region, 's3')
    );

    $authorization = sprintf(
        'AWS4-HMAC-SHA256 Credential=%s/%s, SignedHeaders=%s, Signature=%s',
        $cfg['VIETNIX_S3_ACCESS_KEY'],
        $credentialScope,
        $signedHeaders,
        $signature
    );

    $curlHeaders = [
        'Content-Type: ' . $contentType,
        'Host: ' . $host,
        'x-amz-content-sha256: UNSIGNED-PAYLOAD',
        'x-amz-date: ' . $amzDate,
        'Authorization: ' . $authorization,
    ];
    if ($useAcl) {
        $curlHeaders[] = 'x-amz-acl: public-read';
    }

    return [
        'url' => $endpoint . $canonicalUri,
        'headers' => $curlHeaders,
    ];
}

function putObject(array $cfg, string $key, string $filePath, bool $dryRun): void
{
    $type = contentType(basename($filePath));
    $bucket = $cfg['VIETNIX_S3_BUCKET'];

    if ($dryRun) {
        echo "  [dry-run] s3://$bucket/$key\n";
        return;
    }

    $attempts = [
        ['use_acl' => true],
        ['use_acl' => false],
    ];

    $payload = file_get_contents($filePath);
    if ($payload === false) {
        throw new RuntimeException("Không đọc được file: $filePath");
    }

    $lastError = null;
    $maxRetries = 3;
    $httpCode = 0;
    foreach ($attempts as $attempt) {
        $signed = signPutRequest($cfg, $key, $type, $attempt['use_acl']);

        for ($try = 1; $try <= $maxRetries; $try++) {
            $ch = curl_init($signed['url']);
            curl_setopt_array($ch, [
                CURLOPT_CUSTOMREQUEST => 'PUT',
                CURLOPT_POSTFIELDS => $payload,
                CURLOPT_HTTPHEADER => $signed['headers'],
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_CONNECTTIMEOUT => 30,
                CURLOPT_TIMEOUT => 600,
            ]);

            $body = curl_exec($ch);
            $httpCode = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
            $curlError = curl_error($ch);
            curl_close($ch);

            if ($httpCode >= 200 && $httpCode < 300) {
                return;
            }

            $lastError = $curlError !== '' ? $curlError : "HTTP $httpCode: $body";
            $retryable = $curlError !== '' || $httpCode === 0 || $httpCode >= 500;
            if (!$retryable || $try === $maxRetries) {
                break 2;
            }
            sleep($try * 2);
        }

        if ($httpCode !== 400 && $httpCode !== 403) {
            break;
        }
    }

    throw new RuntimeException("Upload thất bại s3://$bucket/$key — $lastError");
}

function publicUrl(string $base, string $key): string
{
    return rtrim($base, '/') . '/' . $key;
}

function lessonDirs(string $downloads): array
{
    $dirs = [];
    foreach (scandir($downloads) as $name) {
        if ($name === '.' || $name === '..' || str_starts_with($name, '.')) {
            continue;
        }
        $path = $downloads . DIRECTORY_SEPARATOR . $name;
        if (is_dir($path)) {
            $dirs[] = $path;
        }
    }
    sort($dirs);

    return $dirs;
}

function resolveLessonDirs(string $downloads, array $filterNames): array
{
    if ($filterNames === []) {
        return lessonDirs($downloads);
    }

    $dirs = [];
    foreach ($filterNames as $name) {
        $name = basename(trim($name, '/'));
        $path = $downloads . DIRECTORY_SEPARATOR . $name;
        if (!is_dir($path)) {
            fwrite(STDERR, "Không tìm thấy folder: $name (trong $downloads)\n");
            exit(1);
        }
        $dirs[] = $path;
    }
    sort($dirs);

    return $dirs;
}

function collectFiles(string $dir): array
{
    $files = [];
    $iterator = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator($dir, FilesystemIterator::SKIP_DOTS)
    );

    foreach ($iterator as $file) {
        if (!$file->isFile() || str_starts_with($file->getFilename(), '.')) {
            continue;
        }
        $files[] = $file->getPathname();
    }

    sort($files);

    return $files;
}

// --- main ---

$dryRun = in_array('--dry-run', $argv, true);
$onlyHls = in_array('--only-hls', $argv, true);
$downloads = 'downloads';
$filterFolders = [];
foreach ($argv as $i => $arg) {
    if ($arg === '--downloads' && isset($argv[$i + 1])) {
        $downloads = $argv[$i + 1];
    }
    if ($arg === '--folder' && isset($argv[$i + 1])) {
        $filterFolders[] = $argv[$i + 1];
    }
}

if (!is_dir($downloads)) {
    fwrite(STDERR, "Không tìm thấy thư mục: $downloads\n");
    exit(1);
}

$cfg = loadEnv(__DIR__ . '/.env');
$baseKey = trim($cfg['VIETNIX_S3_BASE_KEY'], '/');
$bucket = $cfg['VIETNIX_S3_BUCKET'];
$folders = resolveLessonDirs($downloads, $filterFolders);

if ($folders === []) {
    fwrite(STDERR, "Không có folder bài học trong $downloads\n");
    exit(1);
}

echo "Upload -> s3://$bucket/$baseKey/\n";
echo 'Public URL base: ' . publicUrl($cfg['VIETNIX_S3_PUBLIC_URL'], $baseKey) . "/\n\n";

$totalFiles = 0;
$playlists = [];

foreach ($folders as $lessonDir) {
    $lessonName = basename($lessonDir);
    echo "==> $lessonName\n";

    foreach (collectFiles($lessonDir) as $localFile) {
        $rel = substr($localFile, strlen($lessonDir) + 1);
        $rel = str_replace(DIRECTORY_SEPARATOR, '/', $rel);
        if ($onlyHls && !str_starts_with($rel, 'hls/') && !str_starts_with($rel, 'hls_vocal/')) {
            continue;
        }
        $key = $baseKey . '/' . $lessonName . '/' . $rel;

        if (!$dryRun) {
            echo '    ' . $rel . "\n";
        }
        putObject($cfg, $key, $localFile, $dryRun);
        $totalFiles++;

        if (basename($localFile) === 'index.m3u8') {
            $stream = basename(dirname($localFile));
            $playlists[] = [$lessonName, $stream, publicUrl($cfg['VIETNIX_S3_PUBLIC_URL'], $key)];
        }
    }
}

echo "\nXong: " . count($folders) . " bài, $totalFiles file.\n";

if ($playlists !== []) {
    echo "\nPlaylist URLs:\n";
    sort($playlists);
    foreach ($playlists as [$lesson, $stream, $url]) {
        echo "  $lesson/$stream: $url\n";
    }
}
