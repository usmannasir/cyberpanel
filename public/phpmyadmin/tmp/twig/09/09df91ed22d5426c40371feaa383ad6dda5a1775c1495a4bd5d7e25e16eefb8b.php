<?php

use Twig\Environment;
use Twig\Error\LoaderError;
use Twig\Error\RuntimeError;
use Twig\Extension\SandboxExtension;
use Twig\Markup;
use Twig\Sandbox\SecurityError;
use Twig\Sandbox\SecurityNotAllowedTagError;
use Twig\Sandbox\SecurityNotAllowedFilterError;
use Twig\Sandbox\SecurityNotAllowedFunctionError;
use Twig\Source;
use Twig\Template;

/* header.twig */
class __TwigTemplate_c9024dbab68c1360dc797ea19d8a03ab3c8c0d82280cce85cb7dc119d5b210f2 extends \Twig\Template
{
    private $source;
    private $macros = [];

    public function __construct(Environment $env)
    {
        parent::__construct($env);

        $this->source = $this->getSourceContext();

        $this->parent = false;

        $this->blocks = [
        ];
    }

    protected function doDisplay(array $context, array $blocks = [])
    {
        $macros = $this->macros;
        // line 1
        echo "<!doctype html>
<html lang=\"";
        // line 2
        echo twig_escape_filter($this->env, ($context["lang"] ?? null), "html", null, true);
        echo "\" dir=\"";
        echo twig_escape_filter($this->env, ($context["text_dir"] ?? null), "html", null, true);
        echo "\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1, shrink-to-fit=no\">
  <meta name=\"referrer\" content=\"no-referrer\">
  <meta name=\"robots\" content=\"noindex,nofollow\">
  <meta http-equiv=\"X-UA-Compatible\" content=\"IE=Edge\">
  ";
        // line 9
        if ( !($context["allow_third_party_framing"] ?? null)) {
            // line 10
            echo "<style id=\"cfs-style\">html{display: none;}</style>";
        }
        // line 12
        echo "
  <link rel=\"icon\" href=\"favicon.ico\" type=\"image/x-icon\">
  <link rel=\"shortcut icon\" href=\"favicon.ico\" type=\"image/x-icon\">
  ";
        // line 15
        if (($context["is_print_view"] ?? null)) {
            // line 16
            echo "    <link rel=\"stylesheet\" type=\"text/css\" href=\"";
            echo twig_escape_filter($this->env, ($context["base_dir"] ?? null), "html", null, true);
            echo "print.css?";
            echo twig_escape_filter($this->env, ($context["version"] ?? null), "html", null, true);
            echo "\">
  ";
        } else {
            // line 18
            echo "    <link rel=\"stylesheet\" type=\"text/css\" href=\"";
            echo twig_escape_filter($this->env, ($context["theme_path"] ?? null), "html", null, true);
            echo "/jquery/jquery-ui.css\">
    <link rel=\"stylesheet\" type=\"text/css\" href=\"";
            // line 19
            echo twig_escape_filter($this->env, ($context["base_dir"] ?? null), "html", null, true);
            echo "js/vendor/codemirror/lib/codemirror.css?";
            echo twig_escape_filter($this->env, ($context["version"] ?? null), "html", null, true);
            echo "\">
    <link rel=\"stylesheet\" type=\"text/css\" href=\"";
            // line 20
            echo twig_escape_filter($this->env, ($context["base_dir"] ?? null), "html", null, true);
            echo "js/vendor/codemirror/addon/hint/show-hint.css?";
            echo twig_escape_filter($this->env, ($context["version"] ?? null), "html", null, true);
            echo "\">
    <link rel=\"stylesheet\" type=\"text/css\" href=\"";
            // line 21
            echo twig_escape_filter($this->env, ($context["base_dir"] ?? null), "html", null, true);
            echo "js/vendor/codemirror/addon/lint/lint.css?";
            echo twig_escape_filter($this->env, ($context["version"] ?? null), "html", null, true);
            echo "\">
    <link rel=\"stylesheet\" type=\"text/css\" href=\"";
            // line 22
            echo twig_escape_filter($this->env, ($context["theme_path"] ?? null), "html", null, true);
            echo "/css/theme";
            echo (((($context["text_dir"] ?? null) == "rtl")) ? ("-rtl") : (""));
            echo ".css?";
            echo twig_escape_filter($this->env, ($context["version"] ?? null), "html", null, true);
            echo "&nocache=";
            // line 23
            echo twig_escape_filter($this->env, ($context["unique_value"] ?? null), "html", null, true);
            echo twig_escape_filter($this->env, ($context["text_dir"] ?? null), "html", null, true);
            if ( !twig_test_empty(($context["server"] ?? null))) {
                echo "&server=";
                echo twig_escape_filter($this->env, ($context["server"] ?? null), "html", null, true);
            }
            echo "\">
    <link rel=\"stylesheet\" type=\"text/css\" href=\"";
            // line 24
            echo twig_escape_filter($this->env, ($context["theme_path"] ?? null), "html", null, true);
            echo "/css/printview.css?";
            echo twig_escape_filter($this->env, ($context["version"] ?? null), "html", null, true);
            echo "\" media=\"print\" id=\"printcss\">
  ";
        }
        // line 26
        echo "  <title>";
        echo twig_escape_filter($this->env, ($context["title"] ?? null), "html", null, true);
        echo "</title>
  ";
        // line 27
        echo ($context["scripts"] ?? null);
        echo "
  <noscript><style>html{display:block}</style></noscript>
</head>
<body";
        // line 30
        (( !twig_test_empty(($context["body_id"] ?? null))) ? (print (twig_escape_filter($this->env, (" id=" . ($context["body_id"] ?? null)), "html", null, true))) : (print ("")));
        echo ">
  ";
        // line 31
        echo ($context["navigation"] ?? null);
        echo "
  ";
        // line 32
        echo ($context["custom_header"] ?? null);
        echo "
  ";
        // line 33
        echo ($context["load_user_preferences"] ?? null);
        echo "

  ";
        // line 35
        if ( !($context["show_hint"] ?? null)) {
            // line 36
            echo "    <span id=\"no_hint\" class=\"hide\"></span>
  ";
        }
        // line 38
        echo "
  ";
        // line 39
        if (($context["is_warnings_enabled"] ?? null)) {
            // line 40
            echo "    <noscript>
      ";
            // line 41
            echo call_user_func_array($this->env->getFilter('error')->getCallable(), [_gettext("Javascript must be enabled past this point!")]);
            echo "
    </noscript>
  ";
        }
        // line 44
        echo "
  ";
        // line 45
        if ((($context["is_menu_enabled"] ?? null) && (($context["server"] ?? null) > 0))) {
            // line 46
            echo "    ";
            echo ($context["menu"] ?? null);
            echo "
    <span id=\"page_nav_icons\">
      <span id=\"lock_page_icon\"></span>
      <span id=\"page_settings_icon\">
        ";
            // line 50
            echo \PhpMyAdmin\Html\Generator::getImage("s_cog", _gettext("Page-related settings"));
            echo "
      </span>
      <a id=\"goto_pagetop\" href=\"#\">";
            // line 52
            echo \PhpMyAdmin\Html\Generator::getImage("s_top", _gettext("Click on the bar to scroll to top of page"));
            echo "</a>
    </span>
  ";
        }
        // line 55
        echo "
  ";
        // line 56
        echo ($context["console"] ?? null);
        echo "

  <div id=\"page_content\">
    ";
        // line 59
        echo ($context["messages"] ?? null);
        echo "

    ";
        // line 61
        echo ($context["recent_table"] ?? null);
        echo "
";
    }

    public function getTemplateName()
    {
        return "header.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  204 => 61,  199 => 59,  193 => 56,  190 => 55,  184 => 52,  179 => 50,  171 => 46,  169 => 45,  166 => 44,  160 => 41,  157 => 40,  155 => 39,  152 => 38,  148 => 36,  146 => 35,  141 => 33,  137 => 32,  133 => 31,  129 => 30,  123 => 27,  118 => 26,  111 => 24,  102 => 23,  95 => 22,  89 => 21,  83 => 20,  77 => 19,  72 => 18,  64 => 16,  62 => 15,  57 => 12,  54 => 10,  52 => 9,  40 => 2,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "header.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/header.twig");
    }
}
