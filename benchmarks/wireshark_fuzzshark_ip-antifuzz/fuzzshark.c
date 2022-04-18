/* oss-fuzzshark.c
 *
 * Fuzzer variant of Wireshark for oss-fuzz
 *
 * Wireshark - Network traffic analyzer
 * By Gerald Combs <gerald@wireshark.org>
 * Copyright 1998 Gerald Combs
 *
 * SPDX-License-Identifier: GPL-2.0-or-later
 */

#include <config.h>

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>

#include <glib.h>

#include <epan/epan.h>

#include <wsutil/cmdarg_err.h>
#include <wsutil/crash_info.h>
#include <wsutil/filesystem.h>
#include <wsutil/privileges.h>
#include <wsutil/report_message.h>
#include <version_info.h>

#include <wiretap/wtap.h>

#include <epan/color_filters.h>
#include <epan/timestamp.h>
#include <epan/prefs.h>
#include <epan/column.h>
#include <epan/print.h>
#include <epan/epan_dissect.h>
#include <epan/disabled_protos.h>

#ifdef HAVE_PLUGINS
#include <wsutil/plugins.h>
#endif

#include "FuzzerInterface.h"
#include "antifuzz.h"

#define EPAN_INIT_FAIL 2

static column_info fuzz_cinfo;
static epan_t *fuzz_epan;
static epan_dissect_t *fuzz_edt;

/*
 * General errors and warnings are reported with an console message
 * in oss-fuzzshark.
 */
static void
failure_warning_message(const char *msg_format, va_list ap)
{
	fprintf(stderr, "oss-fuzzshark: ");
	vfprintf(stderr, msg_format, ap);
	fprintf(stderr, "\n");
}

/*
 * Open/create errors are reported with an console message in oss-fuzzshark.
 */
static void
open_failure_message(const char *filename, int err, gboolean for_writing)
{
	fprintf(stderr, "oss-fuzzshark: ");
	fprintf(stderr, file_open_error_message(err, for_writing), filename);
	fprintf(stderr, "\n");
}

/*
 * Read errors are reported with an console message in oss-fuzzshark.
 */
static void
read_failure_message(const char *filename, int err)
{
	cmdarg_err("An error occurred while reading from the file \"%s\": %s.", filename, g_strerror(err));
}

/*
 * Write errors are reported with an console message in oss-fuzzshark.
 */
static void
write_failure_message(const char *filename, int err)
{
	cmdarg_err("An error occurred while writing to the file \"%s\": %s.", filename, g_strerror(err));
}

/*
 * Report additional information for an error in command-line arguments.
 */
static void
failure_message_cont(const char *msg_format, va_list ap)
{
	vfprintf(stderr, msg_format, ap);
	fprintf(stderr, "\n");
}

static int
fuzzshark_pref_set(const char *name, const char *value)
{
	char pref[4096];
	char *errmsg = NULL;

	prefs_set_pref_e ret;

	g_snprintf(pref, sizeof(pref), "%s:%s", name, value);

	ret = prefs_set_pref(pref, &errmsg);
	g_free(errmsg);

	return (ret == PREFS_SET_OK);
}

static const nstime_t *
fuzzshark_get_frame_ts(struct packet_provider_data *prov _U_, guint32 frame_num _U_)
{
	static nstime_t empty;

	return &empty;
}

static epan_t *
fuzzshark_epan_new(void)
{
	static const struct packet_provider_funcs funcs = {
		fuzzshark_get_frame_ts,
		NULL,
		NULL,
		NULL
	};

	return epan_new(NULL, &funcs);
}

static dissector_handle_t
get_dissector_handle(const char *table, const char *target)
{
	dissector_handle_t fuzz_handle = NULL;

	if (table != NULL && target != NULL)
	{
		/* search for handle, cannot use dissector_table_get_dissector_handle() cause it's using short-name, and I already used filter name in samples ;/ */
		GSList *handle_list = dissector_table_get_dissector_handles(find_dissector_table(table));
		while (handle_list)
		{
			dissector_handle_t handle = (dissector_handle_t) handle_list->data;
			const char *handle_filter_name = proto_get_protocol_filter_name(dissector_handle_get_protocol_index(handle));

			if (!strcmp(handle_filter_name, target))
				fuzz_handle = handle;
			handle_list = handle_list->next;
		}
	}
	else if (target != NULL)
	{
		fuzz_handle = find_dissector(target);
	}

	return fuzz_handle;
}

static void
fuzz_prefs_apply(void)
{
	/* Turn off fragmentation for some protocols */
	fuzzshark_pref_set("ip.defragment", "FALSE");
	fuzzshark_pref_set("ipv6.defragment", "FALSE");
	fuzzshark_pref_set("wlan.defragment", "FALSE");
	fuzzshark_pref_set("tcp.desegment_tcp_streams", "FALSE");

	/* Notify all registered modules that have had any of their preferences changed. */
	prefs_apply_all();
}

static int
fuzz_init(int argc _U_, char **argv)
{
	GString             *comp_info_str;
	GString             *runtime_info_str;
	char                *init_progfile_dir_error;

	char                *err_msg = NULL;
	e_prefs             *prefs_p;
	int                  ret = EXIT_SUCCESS;
	size_t               i;

	const char *fuzz_target =
#if defined(FUZZ_DISSECTOR_TARGET)
		FUZZ_DISSECTOR_TARGET;
#else
		getenv("FUZZSHARK_TARGET");
#endif

	const char *disabled_dissector_list[] =
	{
#ifdef FUZZ_DISSECTOR_LIST
		FUZZ_DISSECTOR_LIST ,
#endif
		"snort"
	};

	dissector_handle_t fuzz_handle = NULL;

	/* In oss-fuzz running environment g_get_home_dir() fails:
	 * (process:1): GLib-WARNING **: getpwuid_r(): failed due to unknown user id (0)
	 * (process:1): GLib-CRITICAL **: g_once_init_leave: assertion 'result != 0' failed
	 *
	 * Avoid GLib-CRITICAL by setting some XDG environment variables.
	 */
	g_setenv("XDG_CACHE_HOME", "/not/existing/directory", 0);  /* g_get_user_cache_dir() */
	g_setenv("XDG_CONFIG_HOME", "/not/existing/directory", 0); /* g_get_user_config_dir() */
	g_setenv("XDG_DATA_HOME", "/not/existing/directory", 0);   /* g_get_user_data_dir() */

	g_setenv("WIRESHARK_DEBUG_WMEM_OVERRIDE", "simple", 0);
	g_setenv("G_SLICE", "always-malloc", 0);

	cmdarg_err_init(failure_warning_message, failure_message_cont);

	/*
	 * Get credential information for later use, and drop privileges
	 * before doing anything else.
	 * Let the user know if anything happened.
	 */
	init_process_policies();
#if 0 /* disable setresgid(), it fails with -EINVAL https://github.com/google/oss-fuzz/pull/532#issuecomment-294515463 */
	relinquish_special_privs_perm();
#endif

	/*
	 * Attempt to get the pathname of the executable file.
	 */
	init_progfile_dir_error = init_progfile_dir(argv[0]);
	if (init_progfile_dir_error != NULL)
		fprintf(stderr, "fuzzshark: Can't get pathname of oss-fuzzshark program: %s.\n", init_progfile_dir_error);

	/* Get the compile-time version information string */
	comp_info_str = get_compiled_version_info(NULL, epan_get_compiled_version_info);

	/* Get the run-time version information string */
	runtime_info_str = get_runtime_version_info(epan_get_runtime_version_info);

	/* Add it to the information to be reported on a crash. */
	ws_add_crash_info("OSS Fuzzshark (Wireshark) %s\n"
	     "\n"
	     "%s"
	     "\n"
	     "%s",
	     get_ws_vcs_version_info(),
	     comp_info_str->str,
	     runtime_info_str->str);
	g_string_free(comp_info_str, TRUE);
	g_string_free(runtime_info_str, TRUE);

	init_report_message(failure_warning_message, failure_warning_message,
	     open_failure_message, read_failure_message, write_failure_message);

	timestamp_set_type(TS_RELATIVE);
	timestamp_set_precision(TS_PREC_AUTO);
	timestamp_set_seconds_type(TS_SECONDS_DEFAULT);

	wtap_init(TRUE);

	/* Register all dissectors; we must do this before checking for the
	   "-G" flag, as the "-G" flag dumps information registered by the
	   dissectors, and we must do it before we read the preferences, in
	   case any dissectors register preferences. */
	if (!epan_init(NULL, NULL, FALSE))
	{
		ret = EPAN_INIT_FAIL;
		goto clean_exit;
	}

	/* Load libwireshark settings from the current profile. */
	prefs_p = epan_load_settings();

	if (!color_filters_init(&err_msg, NULL))
	{
		fprintf(stderr, "%s\n", err_msg);
		g_free(err_msg);
	}

	for (i = 0; i < G_N_ELEMENTS(disabled_dissector_list); i++)
	{
		const char *item = disabled_dissector_list[i];

		/* XXX, need to think how to disallow chains like: IP -> .... -> IP,
		 * best would be to disable dissector always, but allow it during initial call. */
		if (fuzz_target == NULL || strcmp(fuzz_target, item))
		{
			fprintf(stderr, "oss-fuzzshark: disabling: %s\n", item);
			proto_disable_proto_by_name(item);
		}
	}

	fuzz_prefs_apply();

	/* Build the column format array */
	build_column_format_array(&fuzz_cinfo, prefs_p->num_cols, TRUE);

#if defined(FUZZ_DISSECTOR_TABLE) && defined(FUZZ_DISSECTOR_TARGET)
# define FUZZ_EPAN 1
	fprintf(stderr, "oss-fuzzshark: configured for dissector: %s in table: %s\n", fuzz_target, FUZZ_DISSECTOR_TABLE);
	fuzz_handle = get_dissector_handle(FUZZ_DISSECTOR_TABLE, fuzz_target);

#elif defined(FUZZ_DISSECTOR_TARGET)
# define FUZZ_EPAN 2
	fprintf(stderr, "oss-fuzzshark: configured for dissector: %s\n", fuzz_target);
	fuzz_handle = get_dissector_handle(NULL, fuzz_target);

#else
# define FUZZ_EPAN 3
	fprintf(stderr, "oss-fuzzshark: env for dissector: %s\n", fuzz_target);
	fuzz_handle = get_dissector_handle(getenv("FUZZSHARK_TABLE"), fuzz_target);
#endif

#ifdef FUZZ_EPAN
	g_assert(fuzz_handle != NULL);
	register_postdissector(fuzz_handle);
#endif

	fuzz_epan = fuzzshark_epan_new();
	fuzz_edt = epan_dissect_new(fuzz_epan, TRUE, FALSE);

	return 0;
clean_exit:
	wtap_cleanup();
	free_progdirs();
	return ret;
}

#ifdef FUZZ_EPAN
int
LLVMFuzzerTestOneInput(const guint8 *buf, size_t real_len)
{
	antifuzz_init(buf, FLAG_ALL); 
	static guint32 framenum = 0;
	epan_dissect_t *edt = fuzz_edt;

	guint32 len = (guint32) real_len;

	wtap_rec rec;
	frame_data fdlocal;

	memset(&rec, 0, sizeof(rec));

	rec.rec_type = REC_TYPE_PACKET;
	rec.rec_header.packet_header.caplen = len;
	rec.rec_header.packet_header.len = len;

	/* whdr.pkt_encap = WTAP_ENCAP_ETHERNET; */
	rec.rec_header.packet_header.pkt_encap = G_MAXINT16;
	rec.presence_flags = WTAP_HAS_TS | WTAP_HAS_CAP_LEN; /* most common flags... */

	frame_data_init(&fdlocal, ++framenum, &rec, /* offset */ 0, /* cum_bytes */ 0);
	/* frame_data_set_before_dissect() not needed */
	epan_dissect_run(edt, WTAP_FILE_TYPE_SUBTYPE_UNKNOWN, &rec, tvb_new_real_data(buf, len, len), &fdlocal, NULL /* &fuzz_cinfo */);
	frame_data_destroy(&fdlocal);

	epan_dissect_reset(edt);
	return 0;
}

#else
# error "Missing fuzz target."
#endif

int
LLVMFuzzerInitialize(int *argc, char ***argv)
{
	int ret;

	ret = fuzz_init(*argc, *argv);
	if (ret != 0)
		exit(ret);

	return 0;
}

/*
 * Editor modelines  -  http://www.wireshark.org/tools/modelines.html
 *
 * Local variables:
 * c-basic-offset: 8
 * tab-width: 8
 * indent-tabs-mode: t
 * End:
 *
 * vi: set shiftwidth=8 tabstop=8 noexpandtab:
 * :indentSize=8:tabSize=8:noTabs=false:
 */