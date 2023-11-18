<?php

namespace SnappyMail;

class SMime
{
	private array $headers = [];
	private int $flags = 0;
	private int $cipher_algo = OPENSSL_CIPHER_AES_128_CBC;
	private ?string $untrusted_certificates_filename = null;
	private $certificate; // OpenSSLCertificate|array|string
	private $private_key; // OpenSSLAsymmetricKey|OpenSSLCertificate|array|string

	public function decrypt(string $data, $certificate = null, $private_key = null)
	{
		$input_filename = \tempnam(\sys_get_temp_dir(), 'smimein-');
		$output_filename = \tempnam(\sys_get_temp_dir(), 'smimeout-');
		try {
			if (\file_put_contents($input_filename, $data)
			 && \openssl_pkcs7_decrypt(
				$input_filename,
				$output_filename,
				$certificate ?: $this->certificate,
				$private_key ?: $this->private_key
			)) {
				return \file_get_contents($output_filename);
			}
		} finally {
			\unlink($input_filename);
			\unlink($output_filename);
		}
	}

	public function encrypt(string $data, $certificate = null): ?string
	{
		$input_filename = \tempnam(\sys_get_temp_dir(), 'smimein-');
		$output_filename = \tempnam(\sys_get_temp_dir(), 'smimeout-');
		try {
			if (\file_put_contents($input_filename, $data)
			 && \openssl_pkcs7_encrypt(
				$input_filename,
				$output_filename,
				$certificate ?: $this->certificate,
				$this->headers,
				$this->flags,
				$this->cipher_algo
			)) {
				return \file_get_contents($output_filename);
			}
		} finally {
			\unlink($input_filename);
			\unlink($output_filename);
		}
		return null;
	}

	public function sign(string $data, $certificate = null, $private_key = null)
	{
		$input_filename = \tempnam(\sys_get_temp_dir(), 'smimein-');
		$output_filename = \tempnam(\sys_get_temp_dir(), 'smimeout-');
		try {
			if (\file_put_contents($input_filename, $data)
			 && \openssl_pkcs7_sign(
				$input_filename,
				$output_filename,
				$certificate ?: $this->certificate,
				$private_key ?: $this->private_key,
				$this->headers,
				PKCS7_DETACHED,
				$this->untrusted_certificates_filename
			)) {
				return \file_get_contents($output_filename);
			}
		} finally {
			\unlink($input_filename);
			\unlink($output_filename);
		}
		return null;
	}

	public function verify(string $data, $signers_certificates_filename = null)
	{
		$input_filename = \tempnam(\sys_get_temp_dir(), 'smimein-');
		try {
			return \file_put_contents($input_filename, $data)
			 && \openssl_pkcs7_verify(
				$input_filename,
				$flags = 0,
				$signers_certificates_filename ?: null,
				$ca_info = [],
				$untrusted_certificates_filename = null,
				$content = null,
				$output_filename = null
			);
		} finally {
			\unlink($input_filename);
		}
		return false;
	}
}
