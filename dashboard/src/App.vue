<template>
<div>
  <v-app-bar class="app-bar" dense>
    <v-app-bar-title>
      TRAPI Resource Validator
    </v-app-bar-title>
  </v-app-bar>

  <v-app>

    <v-container id="page-header">

      <span v-if="FEATURE_SELECT_TEST_RUN_RESOURCES">
      <v-row v-if="id === null && test_runs_contents !== null" dense>
        <v-col>
          <v-select
            v-model="ara_choice"
            :label="'Choose an ARA'"
            :items="[''].concat(Object.values(test_runs_contents).flatMap(el => el.ARAs))"
            dense></v-select>
        </v-col>
        <v-col>
          <v-select
            v-model="kp_choice"
            :label="'Choose a KP'"
            :items="[''].concat(Object.values(test_runs_contents).flatMap(el => el.KPs))"
            dense></v-select>
        </v-col>
      </v-row>
      </span>

      <v-row dense>
        <!-- TODO: remove blur on click -->
        <v-select v-model="id"
                  :label="loading === null ? 'Choose a previous test run' : ''"
                  :items="test_runs_selections
                          .filter(test_run =>
                          (ara_choice !== '' || kp_choice !== '') ?
                          test_runs_contents[test_run].ARAs.includes(ara_choice)
                          || test_runs_contents[test_run].KPs.includes(kp_choice)
                          || false : true)"
                  :clearable="FEATURE_CLEAR_ID"
                  @click:clear="reinitializeState"
                  @click="handleTestRunSelection"
                  dense>
          <template v-slot:item="{ item }">
            <v-container v-if="test_runs_contents !== null" class="d-flex mb-6" no-gutters>
              <v-row>
              <span class="pa-2 mr-auto">{{ item }}</span>
              <v-spacer/>
              <v-chip v-for="kp in test_runs_contents[item].KPs" class="pa-2" :key="kp+'select'+item">{{ kp }}</v-chip>
              <v-chip v-for="ara in test_runs_contents[item].ARAs" class="pa-2" :key="ara+'select'+item">{{ ara }}</v-chip>
              </v-row>
            </v-container>
            <span v-else>{{ item }}</span>
          </template>
        </v-select>
        <span v-if="FEATURE_RUN_TEST_BUTTON && FEATURE_RUN_TEST_SELECT" style="{ padding-top: 1px; }">
          <span>&nbsp;&nbsp;</span>OR
        </span>
        <span v-if="FEATURE_RUN_TEST_BUTTON">
          &nbsp;&nbsp;
          <v-btn :class="['ml-36']"
                 @click="triggerTestRun">
            Trigger new test run
          </v-btn>
        </span>
      </v-row>
    </v-container>

    <v-container id="page-content">
      <h2>{{id}}</h2>
      <div class="subheading" v-if="loading === true">This may take a minute.</div>
      <v-progress-linear
        v-if="loading"
        v-model="status"
        :buffer-value="100"
        :indeterminate="status < 1">
      </v-progress-linear>

      <span v-if="id !== null && loading === false" :key="`${id}_versions`">
        <span class="subheading"><strong>BioLink:&nbsp;</strong></span><span>{{biolink_range.join(', ')}}</span>&nbsp;
        <span class="subheading"><strong>TRAPI:&nbsp;</strong></span><span>{{trapi_range.join(', ')}}</span>&nbsp;
        <span class="subheading"><strong>x-maturity:&nbsp;</strong></span><span>{{x_maturity_range.join(', ')}}</span>&nbsp;
      </span>
      <v-row>

        <!-- TODO replace event handlers with single filter dispatch event -->
        <!-- Sync? -->
        <!-- Lift scope for translator filter to page scope -->
        <TranslatorFilter :index="index"
                          :subject_categories="subject_categories"
                          :predicates="predicates"
                          :object_categories="object_categories"
                          @kp_filter="$event => { kp_filter = $event }"
                          @ara_filter="$event => { ara_filter = $event }"
                          @predicate_filter="$event => { predicate_filter = $event }"
                          @subject_category_filter="$event => { subject_category_filter = $event }"
                          @object_category_filter="$event => { object_category_filter = $event }"
                          ></TranslatorFilter>
      </v-row>

      <v-tabs v-if="!(loading === null)" v-model="tab">
        <v-tab v-for="item in tabs" v-bind:key="`${item}_tab`">
          {{ item }}
        </v-tab>
      </v-tabs>

      <v-tabs-items v-model="tab" >
        <v-tab-item
          v-for="item in tabs"
          v-bind:key="`${item}_tab_item`"
          >
          <div :name="'Overview'" v-if="tab === 0">
            <v-container v-bind:key="`${id}_overview`" id="page-overview" v-if="loading !== null">

              <v-skeleton-loader
                v-if="loading === true"
                v-bind="attrs"
                type="actions,article,card,chip"
                ></v-skeleton-loader>

              <div v-else-if="stats_summary !== null && loading === false" >
                <h2>All providers</h2><br>

                <v-row no-gutter>
                  <v-col>
                    <vc-piechart
                      :data="reduced_stats_summary"/>
                  </v-col>
                  <v-col :cols="9">
                    <SizeProvider>
                      <div class="wrapper" slot-scope="{ width, height }" :style="{ height: height + 'px' }">
                        <SizeObserver>
                          <strong style="{ marginBottom: 5px }"># edges vs tests</strong>
                          <la-cartesian narrow stacked
                                        :bound="[0]"
                                        :data="combined_provider_summary"
                                        :colors="[status_color('passed'), status_color('failed'), status_color('skipped')]"
                                        :width="width">
                            <la-bar label="passed" prop="passed" :color="status_color('passed')"></la-bar>
                            <la-bar label="failed" prop="failed" :color="status_color('failed')"></la-bar>
                            <la-bar label="skipped" prop="skipped" :color="status_color('skipped')"></la-bar>
                            <la-x-axis class="x-axis" :font-size="10" prop="name"></la-x-axis>
                            <la-y-axis></la-y-axis>
                            <la-tooltip></la-tooltip>
                          </la-cartesian>
                        </SizeObserver>
                      </div>
                    </SizeProvider>
                  </v-col>

                </v-row>

                <TranslatorCategoriesList
                  v-if="categories_index !== null && categories_index !== {}"
                  :resource="'all'"
                  :subject_categories="subject_categories"
                  :object_categories="object_categories"
                  :predicates="predicates"
                  ></TranslatorCategoriesList>

                <br>

                <div v-for="resource_key in filtered_index" :key="resource_key+'index'">
                  <v-chip-group :key="`chip_${resource_key}`">
                    <h3>{{ resource_key }}</h3>&nbsp;
                    <v-chip small><strong>BioLink:&nbsp;</strong> {{ _stats_summary[resource_key].biolink_version }}</v-chip>
                    <v-chip small><strong>TRAPI:&nbsp;</strong> {{ _stats_summary[resource_key].trapi_version }}</v-chip>
                    <v-chip small><strong>x-maturity:&nbsp;</strong> {{ _stats_summary[resource_key].x_maturity }}</v-chip>
                  </v-chip-group><br>

                  <v-row no-gutter>
                    <v-col>
                      <vc-piechart
                        v-once
                        :data="reduce_provider_summary(denormalized_stats_summary.filter(stats => stats.provider === resource_key))"/>
                    </v-col>
                    <v-col :cols="9">
                      <SizeProvider>
                        <div class="wrapper" slot-scope="{ width, height }" :style="{ height: height + 'px' }">
                          <SizeObserver>
                            <strong style="{ marginBottom: 5px }"># edges vs tests</strong>
                            <la-cartesian narrow stacked
                                          :bound="[0]"
                                          :data="Object.entries(_stats_summary[resource_key].results).map(([name, rest]) => ({ name, ...rest }))"
                                          :colors="[status_color('passed'), status_color('failed'), status_color('skipped')]"
                                          :width="width">
                              <la-bar label="passed" prop="passed" :color="status_color('passed')"></la-bar>
                              <la-bar label="failed" prop="failed" :color="status_color('failed')"></la-bar>
                              <la-bar label="skipped" prop="skipped" :color="status_color('skipped')"></la-bar>
                              <la-x-axis class="x-axis" :font-size="10" prop="name"></la-x-axis>
                              <la-y-axis></la-y-axis>
                              <la-tooltip></la-tooltip>
                            </la-cartesian>
                          </SizeObserver>
                        </div>
                      </SizeProvider>
                    </v-col>
                  </v-row>

                  <v-row v-if="resources !== null && Object.keys(resources).length > 0 && reduced_message_summary_stats !== null">
                    <v-col>
                      <vc-piechart
                        v-once
                        :data="reduced_message_summary_stats[resource_key]"/>
                    </v-col>
                    <v-col :cols="9">
                      <SizeProvider>
                        <div class="wrapper" slot-scope="{ width, height }" :style="{ height: height + 'px' }">
                          <SizeObserver>
                            <strong style="{ marginBottom: 5px }">info/warning/error/critical error frequency</strong>
                            <la-cartesian narrow stacked
                                          :bound="[0]"
                                          :data="message_summary_stats[resource_key]"
                                          :width="width"
                                          :colors="[status_color('passed'), status_color('error'), status_color('failed'), status_color('skipped')]">
                              <la-bar label="warning" prop="warning" :color="status_color('skipped')"></la-bar>
                              <la-bar label="info" prop="info" :color="status_color('passed')"></la-bar>
                              <la-bar label="error" prop="error" :color="status_color('error')"></la-bar>
                              <la-bar label="critical" prop="critical" :color="status_color('failed')"></la-bar>
                              <la-x-axis class="x-axis" :font-size="10" prop="name"></la-x-axis>
                              <la-y-axis></la-y-axis>
                              <la-tooltip></la-tooltip>
                            </la-cartesian>
                          </SizeObserver>
                        </div>
                      </SizeProvider>
                    </v-col>
                  </v-row>

                  <!-- Not all ARAs have the same KPs. So need to check for the joint key explicitly. -->
                  <TranslatorCategoriesList
                    v-if="categories_index !== null && categories_index !== {} && !!categories_index[resource_key]"
                    :resource="resource_key"
                    :subject_categories="categories_index[resource_key].subject_category"
                    :object_categories="categories_index[resource_key].object_category"
                    :predicates="categories_index[resource_key].predicate"
                    ></TranslatorCategoriesList>

                </div>

              </div>
            </v-container>
          </div>

          <div :name="'Details'" v-if="tab === 1">
            <v-container v-bind:key="`${id}_details`" id="page-details" v-if="loading !== null">
              <v-row v-if="loading !== null" no-gutter>

                <v-col v-if="loading === true">
                  <v-skeleton-loader
                    v-bind="attrs"
                    type="table"
                    ></v-skeleton-loader>
                </v-col>

                <v-col v-else-if="loading === false">

                  <v-row no-gutter>
                    <v-col sml>
                      <v-radio-group
                        v-once
                        v-model="outcome_filter"
                        row>
                        <v-radio
                          label="All"
                          value="all"
                          ></v-radio>
                        <v-radio
                          label="Pass"
                          value="passed"
                          ></v-radio>
                        <v-radio
                          label="Error"
                          value="failed"
                          ></v-radio>
                        <v-radio
                          label="Fail"
                          value="failed"
                          ></v-radio>
                        <v-radio
                          label="Skip"
                          value="skipped"
                          ></v-radio>
                      </v-radio-group>
                    </v-col>
                  </v-row>

                  <v-row no-gutter>

                    <v-col :cols="8">
                      <v-data-table
                        class="elevation-1"
                        :headers="_headers"
                        :items="filtered_cells"
                        :items-per-page="-1"
                        group-by="_id"
                        selec
                        dense>

                        <!-- TODO: group title formatting and tooltip. potentially just put in the summary? -->

                        <template v-slot:item="{ item }">
                          <tr @mouseover="handleRowOnMouseOver(item)()"
                              @mouseleave="handleRowOnMouseAway(item)()"
                              @mouseup="handleRowOnClick(item)()">
                            <td v-for="[test, result] in Object.entries(item)"
                                v-bind:key="`${test}_${result}`"
                                :style="cellStyle(result.outcome)">

                              <a v-if="!!result.outcome">
                                {{ stateIcon(result.outcome) }}
                              </a>

                              <span v-else-if="test === 'spec'">
                                {{formatCurie(result.subject_category)}}&nbsp;{{formatCurie(result.predicate)}}&nbsp;{{formatCurie(result.object_category)}}
                              </span>

                              <span v-else-if="test !== '_id'">
                                {{ result }}
                              </span>

                            </td>
                          </tr>
                        </template>
                      </v-data-table>
                    </v-col>

                    <v-col :cols="4">
                      <v-card class="details-sidebar-card">
                        <v-card-text v-if="data_table_current_item === null">
                          Hover over a row to show its test results.<br>
                          Click a row to keep its test results displayed.<br>
                          Click it again to unselect it.
                        </v-card-text>
                        <v-card-text v-else>
                          <h2>{{ formatEdge(data_table_current_item["spec"]) }}</h2><br>
                          <h3>{{ formatConcreteEdge(data_table_current_item["spec"]) }}</h3><br>

                          <v-chip-group>
                            <v-chip>{{ stateIcon("critical", icon_only=true) }}&nbsp;Errors: {{ selected_result_message_summary.critical }}</v-chip>
                            <v-chip>{{ stateIcon("errors", icon_only=true) }}&nbsp;Errors: {{ selected_result_message_summary.errors }}</v-chip>
                            <v-chip>{{ stateIcon("warnings", icon_only=true) }}&nbsp;Warnings: {{ selected_result_message_summary.warnings }}</v-chip>
                            <v-chip>{{ stateIcon("information", icon_only=true) }}&nbsp;Information: {{ selected_result_message_summary.information }}</v-chip>
                          </v-chip-group>

                          <v-treeview :items="selected_result_treeview" dense>

                            <template v-slot:prepend="{ item, open }">

                              <span v-if="!!item.data"></span>

                              <div v-else-if="!!item.outcome">
                                {{ stateIcon(item.outcome, icon_only=true) }}
                              </div>
                              <span v-else>
                                {{ !!item.name ? stateIcon(item.name, icon_only=true) : !!item.children && item.children.length === 0 ? '⚫' : '' }}
                              </span>

                            </template>
                            <template v-slot:label="{ item }">

                              <span v-if="!!item.data">
                                <ul>
                                  <li>{{ parseResultCode(item.data.code).subcode }}</li>
                                  <ul class="noindent">
                                    <li v-for="result_data in Object.entries(item.data)" v-if="result_data[0] !== 'code'" :key="result_data+Math.random()">
                                      <b>{{ result_data[0] }}: </b> {{ result_data[1] }}<br>
                                    </li>
                                  </ul>
                                </ul>
                              </span>
                              <span v-else>
                                {{ item.name }}
                              </span>

                            </template>
                            <template v-slot:append="{ item }">

                              <span v-if="['critical', 'errors', 'warnings', 'information'].includes(item.name)">
                                {{ item.children.length }}
                              </span>
                              <span v-else-if="!!!item.data">
                                <span v-for="([name, val], i) in Object.entries(countResultMessagesWithCode(item.children.flatMap(item => item.children).map(item => item.data)))" :key="item+[name, val]+i">
                                  <span v-if="val > 0">
                                    {{ stateIcon(name, icon_only=true) }}
                                    &nbsp;{{ val }}
                                  </span>
                                </span>
                              </span>

                            </template>

                          </v-treeview>

                        </v-card-text>
                      </v-card>
                    </v-col>
                  </v-row>
                </v-col>
              </v-row>

            </v-container>
          </div>
          <div :name="'Recommendations'" v-if="tab === 2">

            <v-container>
              <v-row>
                <v-col>
                  <v-btn @click="handleJsonDownload(`${id}_recommendations_${resource}`, recommendations)">
                    Download All Test Recommendations
                  </v-btn>
                </v-col>
              </v-row>

              <span v-for="resource in filtered_index" :key="resource">

                <v-row>
                  <v-col class="d-flex justify-space-between">
                    <h2>{{ resource }}</h2>
                    <v-btn @click="handleJsonDownload(`${id}_recommendations_${resource}`, recommendations[resource])">
                      Download Recommendations for {{ resource }}
                    </v-btn>
                  </v-col>
                </v-row>
                <v-row>

                  <v-col v-for="message_type in Object.keys(cleaned_recommendations[resource])" :key="resource+message_type">
                    <v-card>

                      <v-card-title>
                        {{ message_type | capitalize }}
                      </v-card-title>

                      <v-card-text>
                        <v-treeview v-if="recommendations_treeview !== null"
                                    item-key="name"
                                    :items="recommendations_treeview[resource][message_type]">
                          <template v-slot:label="{ item, open }">
                            <span v-if="item.type === 'code'">
                              <h3>{{item.name}}</h3>
                              <b>({{ cleaned_recommendations[resource][message_type][item.name].count.total }} message{{ cleaned_recommendations[resource][message_type][item.name].count.total > 1 ? 's' : ''}}{{ cleaned_recommendations[resource][message_type][item.name].count.total > cleaned_recommendations[resource][message_type][item.name].count.unique ? ` , ${cleaned_recommendations[resource][message_type][item.name].count.unique} unique` : '' }})</b>
                            </span>
                            <span class="text-subtitle-2" v-else-if="item.type === 'test_data'">Test data</span>
                            <span v-else-if="item.type === 'message'">
                              <ul>
                                <li v-for="[detail, detail_value] in Object.entries(item.message)" :key="resource+message_type+code_detail_detail_value+Math.random()">
                                  <span class="text-subtitle-1">{{ detail | capitalize }}:&nbsp;</span>{{detail_value}}<br>
                                </li>
                              </ul>
                            </span>
                            <span v-else>{{ item.name }}</span>
                          </template>
                        </v-treeview>
                      </v-card-text>

                    </v-card>
                  </v-col>
                </v-row>
              </span>
            </v-container>
          </div>
        </v-tab-item>
      </v-tabs-items>
    </v-container>
    <div id="app"></div>
  </v-app>
</div>
</template>

<script>
/* eslint-disable */

import jp from 'jsonpath';

import { isObject, isArray, isString, sortBy, countBy, throttle, debounce } from "lodash";
import * as _ from "lodash";

// Components
import TranslatorFilter from "./components/TranslatorFilter/TranslatorFilter.vue"
import TranslatorCategoriesList from "./components/TranslatorCategoriesList/TranslatorCategoriesList.vue"

// Visualization
import VcPiechart from "vc-piechart";
import 'vc-piechart/dist/lib/vc-piechart.min.css';
import { Cartesian, Line, Bar } from 'laue'

import vuejsStorage from 'vuejs-storage'

// For dynamic resizing
import { SizeProvider, SizeObserver } from 'vue-size-provider'

import fileDownload from 'js-file-download';

// API code in separate file so we can switch between live and mock instance,
// also configure location for API in environment variables and build variables
// TODO: migrate api calls to api library
import axios from "./api.js";

// TODO: provide feature flags as library
const MOCK = process.env.isAxiosMock;
const FEATURE_RUN_TEST_BUTTON = process.env._FEATURE_RUN_TEST_BUTTON;
const FEATURE_RUN_TEST_SELECT = process.env._FEATURE_RUN_TEST_SELECT;
const FEATURE_RECOMMENDATIONS = process.env._FEATURE_RECOMMENDATIONS;
const FEATURE_SELECT_TEST_RUN_RESOURCES = process.env._FEATURE_SELECT_TEST_RUN_RESOURCES;
const FEATURE_REGISTRY_CALL = process.env._FEATURE_REGISTRY_CALL;
const FEATURE_SESSION_STORAGE = process.env._FEATURE_SESSION_STORAGE;
const FEATURE_CLEAR_ID = process.env._FEATURE_CLEAR_ID;

const _initial_state = {
  id: null,
  tab: '',
  registryResults: [],
  test_runs_selections: [],
  test_runs_contents: null,
  status_interval: -1,
  status: -1,
  outcome_filter: "all",
  ara_choice: '',
  kp_choice: '',
  ara_filter: [],
  kp_filter: [],
  predicate_filter: [],
  subject_category_filter: [],
  object_category_filter: [],
  index: null,
  stats_summary: null,
  subject_categories: [],
  object_categories: [],
  predicates: [],
  categories_index: null,
  resources: null,
  data_table_selected: null,
  data_table_selected_item: null,
  data_table_current_item: null,
  data_table_hold_selection: false,
  recommendations: null,
  active: [],
  registry: null,
  loading: null,
  headers: [],
  cells: [],
  token: null,
  hover: false,
}

export default {
  name: 'App',
  components: {
    SizeProvider,
    SizeObserver,
    TranslatorFilter,
    TranslatorCategoriesList,
    VcPiechart,
    Cartesian,
    Bar,
  },
  filters: {
    capitalize: function (value) {
      if (!value) return ''
      value = value.toString()
      return value.charAt(0).toUpperCase() + value.slice(1)
    },
  },
  data() {
    let tabs = ['Overview', 'Details'];
    if (!!FEATURE_RECOMMENDATIONS) tabs.push('Recommendations')
    return {
      MOCK,
      FEATURE_RUN_TEST_BUTTON,
      FEATURE_RUN_TEST_SELECT,
      FEATURE_RECOMMENDATIONS,
      FEATURE_SELECT_TEST_RUN_RESOURCES,
      FEATURE_REGISTRY_CALL,
      FEATURE_SESSION_STORAGE,
      FEATURE_CLEAR_ID,
      tabs,
      ..._initial_state,
    }
  },
  created () {
    if (FEATURE_REGISTRY_CALL) {
      axios.get(`/registry`).then(async response => {
                this.registry = response.data;
            })
        } else {
            axios.get(`/test_runs`).then(response => {
                this.test_runs_selections = response.data.test_runs;
            })
        }
    },
    storage: FEATURE_SESSION_STORAGE ? {
      keys: ['id', 'tab'],
      namespace: 'dashboard-init',
      driver: vuejsStorage.drivers.sessionStorage,
    } : undefined,
    watch: {
        id(id, oldId) {
          if (!_.isEmpty(id)) {
            this.loading = true;
            this.status_interval = setInterval(() => axios.get(`/status?test_run_id=${id}`).then(response => {
                this.status = response.data.percent_complete;
                if (this.status >= 100) {
                    window.clearInterval(this.status_interval)
                }
            }), 3000);
          }
        },
        status(newStatus, oldStatus) {
            if (!!this.id && newStatus >= 100 && (this.headers.length === 0 && this.cells.length === 0)) {
                axios.get(`/index?test_run_id=${this.id}`).then(response => {
                    this.index = {
                        "KP": {},
                        "ARA": {},
                        ...response.data.summary
                    }
                })
                axios.get(`/summary?test_run_id=${this.id}`).then(response => {
                    // override a summary that is by default empty, but accessible
                    // necessary because the summary API could return only KPs or only ARAs, and return only those
                    // to avoid conditionals we make the object total
                    this.stats_summary = {
                        "KP": {},
                        "ARA": {},
                        ...response.data.summary
                    }
                    // forcing the table data to be synchronous with receiving summary data, since making it reactive lead to problems
                    this.makeTableData(this.id, this.stats_summary)
                })
                this.loading = false;
                this.status = -1;
            }
        },
        index: {
            handler(newIndex, oldIndex) {
                if (newIndex !== null) {
                    this.getAllCategories(this.id, newIndex);
                    this.getAllRecommendations(this.id, newIndex);
                };
            },
        },
        test_runs_selections: {
            handler(newTestRuns, oldTestRuns) {
                if (!FEATURE_REGISTRY_CALL) {
                    Promise.all(newTestRuns.map(test_run =>
                        axios.get(`/index?test_run_id=${test_run}`).then(response => {
                            const { KP, ARA } = response.data.summary;
                            return {
                                "test_run_id": test_run,
                                "KPs": !!KP ? KP : [],
                                "ARAs": !!ARA ? Object.keys(ARA) : [],
                            }
                        })
                    )).then(values => {
                        const grouped_values = _.groupBy(values, 'test_run_id');
                        let test_runs_contents = {};
                        for (let key in grouped_values) {
                            if (!!!test_runs_contents[key]) test_runs_contents[key] = { 'KPs': [], 'ARAs': [] };
                            test_runs_contents[key]["KPs"].push(...grouped_values[key][0]["KPs"])
                            test_runs_contents[key]["ARAs"].push(...grouped_values[key][0]["ARAs"])
                        }
                        this.test_runs_contents = test_runs_contents;
                        return test_runs_contents;
                    })
                }
            },
            deep: true
        }
    },
    computed: {
        selected_result_message_summary() {
            if (!!!this.data_table_current_item) {
                return {
                    "critical": 0,
                    "errors": 0,
                    "warnings": 0,
                    "information": 0,
                }
            }
            return this.countResultMessages(this.data_table_current_item)
        },
        selected_result_treeview() {
            if (!!!this.data_table_current_item) return [];
            return this.item_to_treeview_entry(this.data_table_current_item);
        },
        // TODO: merge these range computations into one scope
        trapi_range() {
            let trapi_versions = [];
            if (!!this.stats_summary && !_.isEmpty(this.stats_summary)) {
                trapi_versions.push(...Object.entries(this.stats_summary.KP).map(([_, entry]) => entry.trapi_version));
                trapi_versions.push(...Object.entries(this.stats_summary.ARA).flatMap(([_, entry]) => Object.entries(entry.kps).map(([_, entry]) => entry.trapi_version)));
            }
            return _(trapi_versions).uniq().omitBy(_.isUndefined).omitBy(_.isNull).sort().values()
        },
        biolink_range() {
            let biolink_versions = [];
            if (!!this.stats_summary && !_.isEmpty(this.stats_summary)) {
                biolink_versions.push(...Object.entries(this.stats_summary.KP).map(([_, entry]) => entry.biolink_version));
                biolink_versions.push(...Object.entries(this.stats_summary.ARA).flatMap(([_, entry]) => Object.entries(entry.kps).map(([_, entry]) => entry.biolink_version)));
            }
            return _(biolink_versions).uniq().omitBy(_.isUndefined).omitBy(_.isNull).sort().values();
        },
        x_maturity_range() {
            let x_maturities = [];
            if (!!this.stats_summary && !_.isEmpty(this.stats_summary)) {
                x_maturities.push(...Object.entries(this.stats_summary.KP).map(([_, entry]) => entry.x_maturity));
                x_maturities.push(...Object.entries(this.stats_summary.ARA).flatMap(([_, entry]) => Object.entries(entry.kps).map(([_, entry]) => entry.x_maturity)));
            }
            return _(x_maturities).uniq().omitBy(_.isUndefined).omitBy(_.isNull).sort().values();
        },
        all_categories() {
            if (!!this.id && !!this.index) {
                return this.getAllCategories(this.id, this.index)
            } else {
                return {
                    subject_categories: [],
                    object_categories: [],
                    predicates: [],
                }
            }
        },
        denormalized_stats_summary() {
            if (this.stats_summary !== null) {
                const combined_results = {
                    ...this.stats_summary.KP,
                    // TODO reduce across keys in 'kp'; split the denormalization below between KP and ARA then concat
                    ...this.stats_summary.ARA,
                };
                return Object.keys(combined_results)
                    .flatMap(provider_key => {
                        if (!!combined_results[provider_key].kps) {
                            return Object.keys(combined_results[provider_key].kps)
                                .flatMap(kp_key => {
                                    return this.denormalize_provider_summary(combined_results[provider_key].kps[kp_key], `${provider_key}_${kp_key}`)
                                })
                        }
                        return this.denormalize_provider_summary(combined_results[provider_key], provider_key)
                    });

            } else {
                return [];
            }
        },
        flat_index() {
          if (!!!this.index) return []
          return [
            ...Object.keys(this.index.ARA).flatMap(ara_key => this.index.ARA[ara_key].map(kp_key => `${ara_key}_${kp_key}`)),
            ...this.index.KP
          ]
        },
        filtered_index() {
            if (this.flat_index.length === 0) return []
            return this.flat_index.filter(key => {
                return this.ara_filter.length > 0 || this.kp_filter.length > 0 ?
                    _.every(this.ara_filter.concat(this.kp_filter), provider_name => _.includes(key, provider_name))
                 || _.some(this.kp_filter, kp => _.includes(key, kp))
                 : true
            })
        },
        denormalized_message_summary() {
            if (!!!this.recommendations) return null;
            return this.flat_index.reduce((acc, resource_key) =>
              _.set(acc, resource_key, this.message_summary_for_resource(this.recommendations[resource_key])), {})
        },
        message_summary_stats() {
            if (!!!this.denormalized_message_summary) return null;
            let message_summary_stats = {};
            this.flat_index.reduce((acc, resource_key) => {
                acc[resource_key] = Object.keys(this.denormalized_message_summary[resource_key]).map(code => ({
                  'name': this.parseResultCode(code).subcode,
                  'error': 0,
                  'warning': 0,
                  'information': 0,
                  [this.parseResultCode(code).type]: this.denormalized_message_summary[resource_key][code].length
                }))
             return acc;
            }, message_summary_stats)
            return message_summary_stats;
        },
        reduced_message_summary_stats() {
          if (!!!this.message_summary_stats) return null;
          return this.flat_index.reduce((acc, resource_key) => {
            const entries = this.message_summary_stats[resource_key]
              .reduce((acc, item) => {
                acc.warning += item.warning
                acc.information += item.information
                acc.error += item.error
                return acc;
              }, {
                'warning': 0,
                'error': 0,
                'information': 0,
              })
            const items = Object.entries(entries).map(([label, value]) => ({
              label,
              value,
              color: this.status_color(label)
            }))
            return _.set(acc, resource_key, items)
         }, {});
        },
        reduced_stats_summary() {
            return this.reduce_provider_summary(this.denormalized_stats_summary)
        },
        _headers() {
            return this.headers
                .concat(['critical', 'errors', 'information', 'warnings'])
                .sort(orderByArrayFunc(['spec', 'critical', 'errors', 'information', 'warnings']))
                .map(el => ({
                    text: el,
                    value: el,
                    filterable: true,
                    sortable: true,
                    sort: (a, b) => {
                        if (!!a.outcome && !!b.outcome)
                            return a.outcome.localeCompare(b.outcome)
                        if (!!a.spec && !!b.spec)
                            return `${a.spec.subject}--${a.spec.predicate}->${a.spec.object}`.localeCompare(`${b.spec.subject}--${b.spec.predicate}->${b.spec.object}`)
                        else
                            return a - b;
                    }
                }))
        },
        denormalized_cells() {
            // inject new columns for message counts
            const __cells = this.cells.map(el => ({
                ...Object.fromEntries(this.headers.map(header => [header, {}])),
                ...el,
                ...this.countResultMessages(el),
            }));
            const ___cells = __cells.map(cell =>
                Object.fromEntries(Object.entries(cell).sort(([a, _], [b, __]) => orderByArrayFunc(['spec', 'critical', 'errors', 'information', 'warnings'])(a, b))));
            return ___cells;
        },
        filtered_cells() {
            const filtered_cells = this.denormalized_cells
                  .filter(el => {
                      return Object.entries(el).some(entry => this.outcome_filter !== "all" ? entry[1].outcome === this.outcome_filter : true)
                          && (this.subject_category_filter.length > 0 ? this.subject_category_filter.includes(el.spec.subject_category) : true)
                          && (this.predicate_filter.length > 0 ? this.predicate_filter.includes(el.spec.predicate) : true)
                          && (this.object_category_filter > 0 ? this.object_category_filter.includes(el.spec.object_category) : true)
                          && (this.ara_filter.length > 0 || this.kp_filter.length > 0 ? _.every(this.ara_filter.concat(this.kp_filter), provider_name => _.includes(el._id, provider_name))
                              || _.some(this.kp_filter, kp => _.includes(el._id, kp))
                              : true)
                 })
            return filtered_cells;
        },
        combined_provider_summary() {
          if (!!!this.stats_summary) return null;
          return this.reduce_provider_by_group(this.combine_provider_summaries(this.stats_summary))
        },
        cleaned_recommendations() {
          const recommendations = this.recommendations;
          if (recommendations === null) return null;

          let cleaned_recommendations = {};
          for (let resource of Object.keys(_.cloneDeep(recommendations))) {
            cleaned_recommendations[resource] = _.omit(recommendations[resource], ['trapi_version', 'biolink_version', 'x_maturity', 'document_key']);
          }

          let unique_recommendations = {};
          for (let resource of Object.keys(cleaned_recommendations)) {
            for (let message_type of Object.keys(cleaned_recommendations[resource])) {
              for (let code of Object.keys(cleaned_recommendations[resource][message_type])) {
                let unique_codes = _.uniqBy(cleaned_recommendations[resource][message_type][code], JSON.stringify)
                _.set(unique_recommendations, `${resource}.${message_type}`, {
                    [code]: {
                        values: unique_codes,
                        count: {
                          unique: unique_codes.length,
                          total:  recommendations[resource][message_type][code].length
                        }
                    }
                })
              }
            }
          }
          return unique_recommendations;
        },
        _stats_summary() {
          if (!!!this.stats_summary) return null;
          return {
            ...Object.keys(this.stats_summary.ARA).reduce((acc, ara_id) => {
              Object.entries(this.stats_summary.ARA[ara_id].kps).forEach(([kp_id, entry]) => {
                Object.assign(acc, { [`${ara_id}_${kp_id}`]: entry })
              })
              return acc;
            }, {}),
            ...this.stats_summary.KP,
          }
        },
        recommendations_treeview() {
            if (!!!this.cleaned_recommendations) return null;
            return Object.keys(this.cleaned_recommendations).reduce((acc, item) => {
                acc[item] = this.recommendationsToTreeView(this.cleaned_recommendations[item])
                return acc;
            }, {})
        }
    },
    methods: {
        message_summary_for_resource(resource_recommendations) {
            return ['critical', 'errors','information','warnings']
                    .flatMap(message_type => jp.nodes(resource_recommendations, `$['${message_type}']`))
                    .reduce((acc, el) => Object.assign(acc, el.value), {})
        },
        item_to_treeview_entry(item) {
            return Object.entries(item).filter(a => !['spec', '_id', 'information', 'warnings', 'errors', 'critical'].includes(a[0]))
                .map(a => ({
                    'name': a[0],
                    'outcome': a[1].outcome,
                    'children': !!a[1].validation ? Object.entries(a[1].validation)
                        .map(a => ({
                            'name': a[0],
                            'children': _(a[1])
                                .uniqBy(object_signature).value()
                                .map(el => ({
                                    'name': "",
                                    'data': el,
                                }))
                        }))
                        .sort((a,b) => a.children.length <= b.children.length) : []
                }))
        },
        handleTestRunSelection ($event) {
            // TODO:
            // // undo focus to ensure scrolling with arrow keys won't suddenly change the user's selected dataset
            // $event.target.blur()
            // console.log($event.target.parentNode)
            this.triggerReloadTestRunSelections()
        },
        handleRowOnClick(item) {
          function lam() {
              this.data_table_selected_item = this.data_table_hold_selection ? this.data_table_selected_item : item;
              this.data_table_current_item = this.data_table_selected_item;
            }
            return lam.bind(this)
        },
        handleRowOnMouseOver(item) {
            function lam() { this.data_table_current_item = this.data_table_hold_selection ? this.data_table_selected_item : item; }
            return throttle(lam.bind(this), 125)
        },
        handleRowOnMouseAway() {
            function lam() { this.data_table_current_item = this.data_table_selected_item; }
            return throttle(lam.bind(this), 125)
        },
        handleJsonDownload(name, data) {
          fileDownload(JSON.stringify(data, null, 4), `${name}.json`)
        },
        async triggerReloadTestRunSelections() {
            let query_params = [];
            if (this.FEATURE_SELECT_TEST_RUN_RESOURCES) {
                if (!_.isEmpty(this.ara_choice)) query_params.push(['ara_id', this.ara_choice])
                if (!_.isEmpty(this.kp_choice)) query_params.push(['kp_id', this.kp_choice])
            }
            axios.get(`/test_runs`).then(response => {
                this.test_runs_selections = response.data.test_runs;
            })
        },
        async triggerTestRun() {
            axios.post(`/run_tests`, {}).then(response => {
                this.id = response.data.test_run_id;
            }).then(this.triggerReloadTestRunSelections)
        },
        status_color: (status) =>
            status === "passed" || status === "information" || status === "info" ? "#00ff00"
            : status === "skipped" || status === "warning" ? "#f0e68c"
            : status === "failed" || status === "error" ? "#ff8000"
            : status === "critical" ? "#f08080"
            : "#000000",
        denormalize_provider_summary(provider_summary, provider_key) {
            //console.log(provider_summary, provider_summary.results, provider_key)
            return Object.entries(provider_summary.results)
                .flatMap((([field, value]) =>
                    {   // console.log(field, value)
                        return Object.keys(value)
                            .map(i => [provider_key, field, i, value[i]])
                    }))
                .map(item => ({
                    'provider': item[0],
                    'test': item[1],
                    'label': item[2],
                    'value': item[3]
                }))
        },
        combine_provider_summaries(provider_summary) {
            const denormalized_kps = Object.keys(provider_summary.KP).flatMap(kp => Object.entries(provider_summary.KP[kp].results).map(el => ({ 'name': el[0], ...el[1]})))
            const denormalized_aras = Object.keys(provider_summary.ARA).flatMap(ara => {
                return Object.keys(provider_summary.ARA[ara].kps).flatMap(kp => Object.entries(provider_summary.KP[kp].results).map(el => ({ 'name': el[0], ...el[1]})))
            })
            return [...denormalized_kps, ...denormalized_aras];
        },
        reduce_provider_summary(denormalized_provider_summary) {
            const tally = {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
            };
            denormalized_provider_summary.forEach(({ label, value }) => {
                if (label !== 'undefined') tally[label] += value;
            });
            return Object.entries(tally).map(([label, value]) => ({
                label,
                value,
                color: this.status_color(label)
            }))
        },
        reduce_provider_by_group(data) {
            const ans = _(data)
                  .groupBy('name')
                  .map((obj, id) => ({
                      name: id,
                      passed: _.sumBy(obj, 'passed'),
                      failed: _.sumBy(obj, 'failed'),
                      skipped: _.sumBy(obj, 'skipped'),
                  }))
                  .value()
            return ans
        },
        async getAllRecommendations(id, index) {

            let resource_promises = [];

            index.KP.forEach(kp_id => {
                resource_promises.push(
                    axios.get(`/recommendations?test_run_id=${id}&kp_id=${kp_id}`)
                        .then(response => {
                            return {
                                [kp_id]: response.data.recommendations
                            };
                        })
                    )
            });
            Object.keys(index.ARA)
                .forEach(ara_id => {
                    index.ARA[ara_id].forEach(kp_id => {
                        resource_promises.push(
                            axios.get(`/recommendations?test_run_id=${id}&kp_id=${kp_id}&ara_id=${ara_id}`)
                                .then(response => {
                                    return {
                                        [ara_id+'_'+kp_id]: response.data.recommendations
                                    };
                                })
                        )
                    })
                });

            Promise.all(resource_promises).then((response => {
                this.recommendations = response.reduce((acc, item) => Object.assign(acc, item), {});
            }));

        },
        async getAllCategories(id, index) {

            const categories = {
                subject_category: [],
                predicate: [],
                object_category: [],
            };
            const addFromKPs = (id, kpSummary) => {
                Object.values(kpSummary.test_edges).forEach(el => {
                    if (isObject(el)) {

                        let pre_categories_index = _.clone(this.categories_index);

                        if (pre_categories_index === null) {
                            pre_categories_index = {};
                        }
                        if (!!!pre_categories_index[id]) {
                            pre_categories_index[id] = {};
                            pre_categories_index[id].subject_category = [];
                            pre_categories_index[id].object_category = [];
                            pre_categories_index[id].predicate = [];
                        }

                        pre_categories_index[id].subject_category.push(el.test_data.subject_category);
                        pre_categories_index[id].predicate.push(el.test_data.predicate);
                        pre_categories_index[id].object_category.push(el.test_data.object_category);
                        this.categories_index = pre_categories_index;

                        categories.subject_category.push(el.test_data.subject_category)
                        categories.predicate.push(el.test_data.predicate)
                        categories.object_category.push(el.test_data.object_category)
                    }
                });

            }

            let new_resources = {};
            let resource_promises = [];

            // TODO: prevent duplicate call to resource
            index.KP.forEach(kp_id => {
                resource_promises.push(
                    axios.get(`/resource?test_run_id=${id}&kp_id=${kp_id}`)
                        .then(response => {
                            addFromKPs(kp_id, response.data.summary)
                            return {
                                [kp_id]: response.data.summary
                            };
                        })
                    )
            });
            Object.keys(index.ARA)
                .forEach(ara_id => {
                    index.ARA[ara_id].forEach(kp_id => {
                        resource_promises.push(
                            axios.get(`/resource?test_run_id=${id}&kp_id=${kp_id}&ara_id=${ara_id}`)
                                .then(response => {
                                    addFromKPs(`${ara_id}_${kp_id}`, response.data.summary)
                                    return {
                                        [ara_id+'_'+kp_id]: response.data.summary
                                    };
                                })
                        )
                    })
                });

            Promise.all(resource_promises).then((response => {
                this.subject_categories = categories.subject_category;
                this.object_categories = categories.object_category;
                this.predicates = categories.predicate;
                this.resources = response.reduce((acc, item) => Object.assign(acc, item), {});
            }))

           return categories;
        },
        reinitializeState() {
          for (let state in _initial_state) {
            this[state] = _initial_state[state];
          }
        },
        makeTableData(id, stats_summary) {
            this.headers = [];
            this.cells = [];

            // TODO: prevent duplicate call to `resource`
            const report = Promise.resolve(stats_summary).then(response => {
                if (response !== null) {
                    const { KP={}, ARA={} } = response;
                    const kp_details = Object.entries(KP).map(([resource_id, value]) => {
                        return axios.get(`/resource?test_run_id=${id}&kp_id=${resource_id}`).then(el => {
                            return {
                                resource_id,  // inject the resource_id into the response
                                ...el,
                            }
                        })
                    });
                    const ara_details = Object.entries(ARA).map(([resource_id, value]) => {
                        return Object.keys(value.kps)
                            .map(key => axios.get(`/resource?test_run_id=${id}&ara_id=${resource_id}&kp_id=${key}`)
                                 .then(el => {
                                     return {
                                         resource_id: `${resource_id}>${key}`,
                                         ...el,
                                     }
                                 }))
                    });
                    return Promise.all(
                        [...kp_details, ...ara_details.flatMap(i=>i)]
                            .map(p => p
                                 .then(value => ({
                                     status: "fulfilled",
                                     value
                                 }))
                                 .then(response => {
                                     if (response.status === "fulfilled") {
                                        const  { headers, cells } = _makeTableData(response.value.resource_id, response.value.data.summary);
                                        // https://forum.vuejs.org/t/performance-issue-with-reactivity-in-a-long-list-flushcallbacks-taking-long/45838/7
                                        for (let header of Array.from(_.uniq(headers))) {
                                          if (!this.headers.includes(header)) {
                                              this.headers.push(header);
                                          }
                                        }
                                        for (let cell of cells) {
                                           this.cells.push(cell);
                                        }
                                     }
                                 })
                                 .catch(reason => ({
                                     status: "rejected",
                                     reason
                                 })))
                    )
                } else {
                    return null;
                }
            })
                  .then(responses => {
                      this.loading = false;
                      this.status = -1;
                  });
        },


        // custom methods for application testing
        tap: el => { console.log("hello", el, this); return el },

        // import methods from packages
        throttle,
        debounce,

        // object manipulation
        omit: (...keys) => object => _.omit(object, keys),
        pick: (...keys) => object => _.pick(object, keys),
        notEmpty: (list) => list.filter(el => el !== ""),
        orderObjectKeysBy(obj, keys) {
            return Object.fromEntries(Object.entries(obj).sort(([a, _], [b, __]) => orderByArrayFunc(keys)(a, b)))
        },

        // `custom-filter` in v-data-table props: https://vuetifyjs.com/en/api/v-data-table/#props
        // adjust cell style:
        // TODO - move on to use style classes instead
        cellStyle(state) {
            let color = "black";
            let backgroundColor = "none";
            if (state === "passed" || state=== "failed") {
                color = "white";
                backgroundColor = this.status_color(state);
            } else if (state === "skipped") {
                backgroundColor = this.status_color(state);
            }
            return {
                color,
                backgroundColor,
                borderLeft: 'solid 1px white',
                borderRight: 'solid 1px white'
            }
        },
        stateIcon (state, icon_only=false) {
            if (state === "passed") {
                return `✅${!icon_only ? ' Pass' : ''}`
            } else if (state === "skipped") {
                return `❓${!icon_only ? ' Skip' : ''}`
            } else if (state === 'warnings') {
                return `⚠️${!icon_only ? ' Warning' : ''}`
            } else if (state === 'errors') {
                return `❗${!icon_only ? ' Error' : ''}`
            } else if (state === "failed" || state === 'critical') {
                return `⛔${!icon_only ? ' Fail' : ''}`
            } else if (state === "information" || state === "info") {
                return `ℹ️${!icon_only ? ' Info': ''}`
            }
            return state
        },
        formatEdge (result) {
            return `(${this.formatCurie(result.subject_category)})--[${this.formatCurie(result.predicate)}]->(${this.formatCurie(result.object_category)})`
        },
        formatConcreteEdge (result) {
            return `(${result.subject})--[${result.predicate}]->(${result.object})`
        },
        formatCurie (curie) {
            return curie.split(':')[1];
        },
        countResultMessages(edge_result) {
            return Object.entries(edge_result).reduce(function (acc, item) {
                let [ left, right ] = item;
                if (!!right && !!right.validation) {
                    const { validation } = right;
                    const { information, warnings, errors, critical } = validation;
                    acc.information += _.uniqBy(information, object_signature).length;
                    acc.warnings += _.uniqBy(warnings, object_signature).length;
                    acc.errors += _.uniqBy(errors, object_signature).length;
                    acc.critical += _.uniqBy(critical, object_signature).length;

                }
                return acc;
            }, {
                critical: 0,
                errors: 0,
                warnings: 0,
                information: 0,
            })
        },
        countResultMessagesWithCode(messages) {
            const initial_count = {
                critical: 0,
                errors: 0,
                warnings: 0,
                information: 0,
            }
            if (!!!messages) return initial_count;
            return messages.reduce((a, i) => {
                if (i.code.startsWith('warning')) a['warnings'] += 1;
                if (i.code.startsWith('info')) a['information'] += 1;
                if (i.code.startsWith('error')) a['errors'] += 1;
                if (i.code.startsWith('critical')) a['critical'] += 1;
                return a;
            }, initial_count)
        },
        parseResultCode(code) {
            const type = code.split('.')[0]
            const subcode = code.split('.').slice(1).join('.');
            return {
                type,
                subcode
            }
        },
        recommendationsToTreeView(recommendations) {
            return Object.keys(recommendations).reduce((message_types, message_type) => {
                const messages = Object.keys(recommendations[message_type]).reduce((codes, code) => {
                        return codes.concat({
                            name: code,
                            type: 'code',
                            children: recommendations[message_type][code].values.map((el, n) => ({
                                id: `${message_type}_${code}_message_${n}`,
                                name: JSON.stringify(el.message),
                                type: 'message',
                                message: el.message,
                                children: [{
                                    id: `${message_type}_${code}_test_data_${n}`,
                                    name: 'test_data',
                                    type: 'test_data',
                                    test_data: el.test_data,
                                    children: [
                                        { name: this.formatConcreteEdge(el.test_data) },
                                        { name: this.formatEdge(el.test_data) }
                                    ]
                                }]
                            }))
                        })
                    }, [])
                message_types[message_type] = messages;
                return message_types;
            }, {})
        }
    }
}

const orderByArrayFunc = array => {
    if (array.length === 0) return (a, b) => 0;
    const sortMap = Object.fromEntries(Object.entries(array.reverse()).map(([a, b]) => [b, a]))
    const sortFunc = (a, b) => {
        const [_a, _b] = [_.get(sortMap, a, -1), _.get(sortMap, b, -1)]
        return _a < _b
    };
    return sortFunc;
}
function orderByPlaceInArray(iterable, array) {
    if (array.length === 0 || iterable.length === 0) return iterable;
    return iterable.sort(orderByArrayFunc(array))
}
// const orderByPlaceInArray_test_case = ['spec', 'information', 'warnings', 'errors', 'critical']
// console.warn(orderByPlaceInArray([], orderByPlaceInArray_test_case))
// console.warn(orderByPlaceInArray(orderByPlaceInArray_test_case, orderByPlaceInArray_test_case))
// console.warn(orderByPlaceInArray(['a', 'b', 'c'], orderByPlaceInArray_test_case))
// console.warn(orderByPlaceInArray(orderByPlaceInArray_test_case.reverse(), orderByPlaceInArray_test_case))
// console.warn(orderByPlaceInArray(orderByPlaceInArray_test_case.concat(['a', 'b', 'c']), orderByPlaceInArray_test_case))

function object_signature(el) {
    return Object.entries(el).flatMap(i=>i).join(';')
}

function _makeTableData(resource_id, report) {
  const test_results = jp.nodes(report.test_edges, "$.*").filter(el => !el.path.includes("document_key"))
  const headers = Array.from(test_results.reduce((acc, item) => {
    const { test_data, results } = item.value;
    if (!!results) Object.keys(results).forEach(key => acc.add(key));    // fields
        return acc;
    }, new Set(["spec"])));
    const cells = test_results.reduce((acc, item) => {
        const { test_data, results } = item.value;
        acc.push({
            _id: resource_id,
            spec: test_data,
            ...results,
        })
        return acc;
    }, []);
    return {
        id: report.test_run_id,
        headers,
        cells,
    };
}

</script>

<style>
#app {
    font-family: 'Avenir', Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    color: #2c3e50;
    padding: 1%;
}
#page-header, #page-content {
    margin: 0;
}
.container {
    max-width: 4000px !important
}
.app-bar {
    font-family: 'Avenir', Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    color: #2c3e50;
}

tr {
    margin-top: 5px;
}
th > span {
    text-align: center;
}
tr.v-row-group__header > td.text-start > button > span > i.mdi-close {
    display: none;
}
.v-tooltip__content {
    background: rgb(97,97,97);
    opacity: 1.0;
}

/* For the barcharts so long names don't overlap */
g.x-axis > g > g:nth-child(2n) text {
    transform: translateY(14px);
    transform-origin: left bottom;
    transform-box: fill-box;
}
g.x-axis > g > g:nth-child(2n) line {
    transform: scaleY(3.25);
    transform-origin: top;
    transform-box: fill-box;
}

ul.noindent {
    margin-left: 5px;
    margin-right: 0px;
    padding-left: 15px;
    padding-right: 0px;
    padding-bottom: 15px;
}

.details-sidebar-card {
    overflow-y: scroll;
}
.details-sidebar-card .v-treeview-node__content > .v-treeview-node__prepend {
    min-width: 0;
}

.details-sidebar-card ul {
    overflow-x: scroll;
}
</style>
