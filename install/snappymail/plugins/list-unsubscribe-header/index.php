<?php

/**
 * Bundled with CyberPanel (see plogical/snappymail_plugin_utilities.py).
 * Upstream: https://github.com/master3395/snappymail-list-unsubscribe-header
 *
 * Adds List-Unsubscribe and List-Unsubscribe-Post on outbound mail (RFC 2369 / RFC 8058).
 */
class ListUnsubscribeHeaderPlugin extends \RainLoop\Plugins\AbstractPlugin
{
	const
		NAME = 'List-Unsubscribe headers',
		AUTHOR = 'Master3395',
		URL = 'https://newstargeted.com/',
		VERSION = '1.1.0',
		RELEASE = '2026-04-11',
		REQUIRED = '2.0.0',
		DESCRIPTION = 'Adds List-Unsubscribe and List-Unsubscribe-Post for bulk/mailing-list best practices.';

	public function Init() : void
	{
		$this->addHook('filter.send-message', 'FilterSendMessage');
	}

	/**
	 * @return array
	 */
	protected function configMapping() : array
	{
		return array(
			\RainLoop\Plugins\Property::NewInstance('unsubscribe_https_url')
				->SetLabel('HTTPS unsubscribe URL')
				->SetType(\RainLoop\Enumerations\PluginPropertyType::URL)
				->SetDescription('Must be https:// — used in List-Unsubscribe (RFC 8058 one-click target).')
				->SetDefaultValue('https://newstargeted.com/list-unsubscribe-endpoint.php'),
			\RainLoop\Plugins\Property::NewInstance('mailto_unsubscribe')
				->SetLabel('Unsubscribe mailto address')
				->SetType(\RainLoop\Enumerations\PluginPropertyType::STRING)
				->SetDescription('Email only (e.g. postmaster@example.com) or full mailto:user@example.com')
				->SetDefaultValue('postmaster@newstargeted.com'),
			\RainLoop\Plugins\Property::NewInstance('one_click_post')
				->SetLabel('Send List-Unsubscribe-Post (one-click)')
				->SetType(\RainLoop\Enumerations\PluginPropertyType::BOOL)
				->SetDescription('RFC 8058 — disable if your HTTPS URL does not accept POST.')
				->SetDefaultValue(true)
		);
	}

	/**
	 * @param \MailSo\Mime\Message $oMessage
	 */
	public function FilterSendMessage(&$oMessage) : void
	{
		if ($oMessage instanceof \MailSo\Mime\Message) {
			$sHttps = \trim((string) $this->Config()->Get('plugin', 'unsubscribe_https_url', 'https://newstargeted.com/list-unsubscribe-endpoint.php'));
			$sMailRaw = \trim((string) $this->Config()->Get('plugin', 'mailto_unsubscribe', 'postmaster@newstargeted.com'));
			$bOneClick = (bool) $this->Config()->Get('plugin', 'one_click_post', true);

			if ($sHttps === '' || !\preg_match('#^https://#i', $sHttps)) {
				$sHttps = 'https://newstargeted.com/list-unsubscribe-endpoint.php';
			}
			if ($sMailRaw === '') {
				$sMailto = 'mailto:postmaster@newstargeted.com';
			} elseif (\stripos($sMailRaw, 'mailto:') === 0) {
				$sMailto = $sMailRaw;
			} else {
				$sMailto = 'mailto:' . $sMailRaw;
			}
			if (!\preg_match('#^mailto:[^<>\s]+$#i', $sMailto)) {
				$sMailto = 'mailto:postmaster@newstargeted.com';
			}

			$sListUnsub = '<' . $sHttps . '>, <' . $sMailto . '>';
			$oMessage->SetCustomHeader(
				\MailSo\Mime\Enumerations\Header::LIST_UNSUBSCRIBE,
				$sListUnsub
			);
			if ($bOneClick) {
				$oMessage->SetCustomHeader('List-Unsubscribe-Post', 'List-Unsubscribe=One-Click');
			}
		}
	}
}
