<template>
<div>
  <v-app-bar class="app-bar" dense>
    <v-app-bar-title>
      TRAPI Resource Validator
    </v-app-bar-title>
  </v-app-bar>

  <v-app>

    <v-container id="page-header">
      <v-row no-gutter>
        <span v-if="FEATURE_RUN_TEST_BUTTON">
          <v-btn :class="['ml-36']"
                 @click="triggerTestRun">Trigger new test run</v-btn>
          &nbsp;&nbsp;</span>
        <span v-if="FEATURE_RUN_TEST_BUTTON && FEATURE_RUN_TEST_SELECT" style="{ padding-top: 1px; }">OR
          <span>&nbsp;&nbsp;</span></span>
        <v-select v-model="id"
                  :label="loading === null ? 'Choose a previous test run' : ''"
                  :items="test_runs_selections"
                  @click="triggerReloadTestRunSelections"
                  dense>
        </v-select>

      </v-row>
    </v-container>

    <v-container id="page-content">

      <h1>{{ id }}</h1>
      <div class="subheading" v-if="loading === true">This may take a minute.</div>
      <v-progress-linear
        v-if="loading"
        v-model="status"
        :buffer-value="100"
        :indeterminate="status < 1">
      </v-progress-linear>

      <span v-if="id !== null && loading === false" :key="`${id}_versions`">
        <span class="subheading"><strong>BioLink:&nbsp;</strong></span><span>{{biolink_range}}</span>&nbsp;
        <span class="subheading"><strong>TRAPI:&nbsp;</strong></span><span>{{trapi_range}}</span>&nbsp;
      </span>

      <v-tabs v-if="!(loading === null)" v-model="tab">
        <v-tab v-for="item in ['Overview', 'Details']" v-bind:key="`${item}_tab`">
          {{ item }}
        </v-tab>
      </v-tabs>

      <v-tabs-items v-model="tab" >
        <v-tab-item
          v-for="item in ['Overview','Details']"
          v-bind:key="`${item}_tab_item`"
          >
          <div v-if="tab === 0" >
            <v-row no-gutter>
              <TranslatorFilter :index="index"
                                @kp_filter="$event => { kp_filter = $event }"
                                @ara_filter="$event => { ara_filter = $event }"
                                @predicate_filter="$event => { predicate_filter = $event }"
                                @subject_category_filter="$event => { subject_category_filter = $event }"
                                @object_category_filter="$event => { object_category_filter = $event }"
                                ></TranslatorFilter>
            </v-row>

            <v-container v-bind:key="`${id}_overview`" id="page-overview" v-if="loading !== null">

              <v-skeleton-loader
                v-if="loading === true"
                v-bind="attrs"
                type="actions,article,card,chip"
                ></v-skeleton-loader>

              <div v-else-if="stats_summary !== null && loading === false">
                <h2>Test Results</h2>
                <h3>All providers</h3><br>

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
                                        :data="reduce_provider_by_group(combine_provider_summaries(stats_summary))"
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

                <span v-if="Object.keys(stats_summary['ARA']).length > 0 && !(kp_filter.length > 0 && ara_filter.length === 0)">

                  <br><h2>ARAs</h2>
                  <div v-for="ara in Object.keys(stats_summary['ARA']).filter(ara => ara_filter.length > 0 ? ara_filter.includes(ara) : true)" v-bind:key="ara">
                    <div v-for="kp in Object.keys(stats_summary['ARA'][ara].kps).filter(kp => kp_filter.length > 0 ? kp_filter.includes(kp) : true)" v-bind:key="`${ara}_${kp}`">

                      <v-chip-group>
                        <h3>{{ ara }}: {{ kp }}</h3>&nbsp;
                        <v-chip small><strong>BioLink:&nbsp;</strong> {{ stats_summary.ARA[ara].kps[kp].biolink_version }}</v-chip>
                        <v-chip small><strong>TRAPI:&nbsp;</strong> {{ stats_summary.ARA[ara].kps[kp].trapi_version }}</v-chip>
                      </v-chip-group><br>

                      <v-row no-gutter>
                        <v-col>
                          <vc-piechart
                            :data="reduce_provider_summary(denormalize_provider_summary(stats_summary['ARA'][ara].kps[kp]))"/>
                        </v-col>
                        <v-col :cols="9">
                          <SizeProvider>
                            <div class="wrapper" slot-scope="{ width, height }" :style="{ height: height + 'px' }">
                              <SizeObserver>
                                <strong style="{ marginBottom: 5px }"># edges vs tests</strong>
                                <la-cartesian narrow stacked
                                              :bound="[0]"
                                              :data="Object.entries(stats_summary['ARA'][ara].kps[kp].results).map(el => ({ 'name': el[0], ...el[1]}))"
                                              :colors="[status_color('passed'), status_color('failed'), status_color('skipped')]"
                                              :width="820">
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

                      <v-row v-if="Object.keys(resources).length > 0">
                        <v-col>
                          <vc-piechart
                            :data="Object.entries(groupedResultMessagesByCode(resources[`${ara}_${kp}`]))
                                   .map(i => [i[0], Object.entries(i[1]).reduce((a, i) => { a += i[1]; return a; }, 0)])
                                   .map(i => ({
                                   'label': i[0],
                                   'value': i[1],
                                   'color': i[0] === 'warning' ? status_color('skipped') : i[0] === 'info' ? status_color('passed') : status_color('failed')
                                   }))"/>
                        </v-col>
                        <v-col :cols="9">
                          <SizeProvider>
                            <div class="wrapper" slot-scope="{ width, height }" :style="{ height: height + 'px' }">
                              <SizeObserver>
                                <strong style="{ marginBottom: 5px }">info/warning/error frequency</strong>
                                <la-cartesian narrow stacked
                                              :bound="[0]"
                                              :data="Object.entries(groupedResultMessagesByCode(resources[`${ara}_${kp}`]))
                                                     .map(i => [i[0], Object.entries(i[1])])
                                                     .flatMap(i => i[1].map(([code, frequency]) => [i[0], [code, frequency]]))
                                                     .map(([type, [code, frequency]]) => ({
                                                     'name': code,
                                                     'warning': 0,
                                                     'info': 0,
                                                     'error': 0,
                                                     [type]: frequency
                                                     }))"
                                              :width="width"
                                              :colors="[status_color('passed'), status_color('failed'), status_color('skipped')]">
                                  <la-bar label="warning" prop="warning" :color="status_color('skipped')"></la-bar>
                                  <la-bar label="info" prop="info" :color="status_color('passed')"></la-bar>
                                  <la-bar label="error" prop="error" :color="status_color('failed')"></la-bar>
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
                        v-if="categories_index !== null && categories_index !== {} && !!categories_index[ara+'_'+kp]"
                        :resource="ara+'_'+kp"
                        :subject_categories="categories_index[ara+'_'+kp].subject_category"
                        :object_categories="categories_index[ara+'_'+kp].object_category"
                        :predicates="categories_index[ara+'_'+kp].predicate"
                        ></TranslatorCategoriesList>

                    </div>
                  </div>
                </span>

                <span v-if="Object.keys(stats_summary['KP']).length > 0 && !(ara_filter.length > 0 && kp_filter.length === 0)">
                  <br><h2>KPs</h2>
                  <div v-for="kp in Object.keys(stats_summary['KP'])
                              .filter(kp => kp_filter.length > 0 ? kp_filter.includes(kp) : true)" v-bind:key="kp" >
                    <v-chip-group>
                      <h3>{{ kp }}</h3>&nbsp;
                      <v-chip small><strong>BioLink:&nbsp;</strong> {{ stats_summary.KP[kp].biolink_version }}</v-chip>
                      <v-chip small><strong>TRAPI:&nbsp;</strong> {{ stats_summary.KP[kp].trapi_version }}</v-chip>
                    </v-chip-group><br>

                    <v-row no-gutter>
                      <v-col>
                        <vc-piechart
                          :data="reduce_provider_summary(denormalize_provider_summary(stats_summary['KP'][kp]))"/>
                      </v-col>
                      <v-col :cols="9">
                        <SizeProvider>
                          <div class="wrapper" slot-scope="{ width, height }" :style="{ height: height + 'px' }">
                            <SizeObserver>
                              <strong style="{ marginBottom: 5px }"># edges vs tests</strong>
                              <la-cartesian narrow stacked
                                            :bound="[0]"
                                            :data="Object.entries(stats_summary['KP'][kp].results).map(el => ({ 'name': el[0], ...el[1]}))"
                                            :width="width"
                                            :colors="[status_color('passed'), status_color('failed'), status_color('skipped')]">
                                <la-bar label="passed" prop="passed" :color="status_color('passed')"></la-bar>
                                <la-bar label="failed" prop="failed" :color="status_color('failed')"></la-bar>
                                <la-bar label="skipped" prop="skipped" :color="status_color('skipped')"></la-bar>
                                <la-x-axis class="x-axis" :font-size="10" prop="name"></la-x-axis>
                                <la-y-axis ></la-y-axis>
                                <la-tooltip></la-tooltip>
                              </la-cartesian>
                            </SizeObserver>
                          </div>
                        </SizeProvider>
                      </v-col>
                    </v-row>

                    <v-row v-if="Object.keys(resources).length > 0">
                      <v-col>
                        <vc-piechart
                          :data="Object.entries(groupedResultMessagesByCode(resources[kp]))
                                 .map(i => [i[0], Object.entries(i[1]).reduce((a, i) => { a += i[1]; return a; }, 0)])
                                 .map(i => ({
                                 'label': i[0],
                                 'value': i[1],
                                 'color': i[0] === 'warning' ? status_color('skipped') : i[0] === 'info' ? status_color('passed') : status_color('failed')
                                 }))"/>
                      </v-col>
                      <v-col :cols="9">
                        <SizeProvider>
                          <div class="wrapper" slot-scope="{ width, height }" :style="{ height: height + 'px' }">
                            <SizeObserver>
                              <strong style="{ marginBottom: 5px }">info/warning/error frequency</strong>
                              <la-cartesian narrow stacked
                                            :bound="[0]"
                                            :data="Object.entries(groupedResultMessagesByCode(resources[kp]))
                                                   .map(i => [i[0], Object.entries(i[1])])
                                                   .flatMap(i => i[1].map(([code, frequency]) => [i[0], [code, frequency]]))
                                                   .map(([type, [code, frequency]]) => ({
                                                   'name': code,
                                                   'warning': 0,
                                                   'info': 0,
                                                   'error': 0,
                                                   [type]: frequency
                                                   }))"
                                            :width="width"
                                            :colors="[status_color('passed'), status_color('failed'), status_color('skipped')]">
                                <la-bar label="warning" prop="warning" :color="status_color('skipped')"></la-bar>
                                <la-bar label="info" prop="info" :color="status_color('passed')"></la-bar>
                                <la-bar label="error" prop="error" :color="status_color('failed')"></la-bar>
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
                      v-if="categories_index !== null && categories_index !== {} && !!categories_index[kp]"
                      :resource="kp"
                      :subject_categories="categories_index[kp].subject_category"
                      :object_categories="categories_index[kp].object_category"
                      :predicates="categories_index[kp].predicate"
                      ></TranslatorCategoriesList>

                  </div>
                </span>
              </div>
            </v-container>
          </div>

          <div v-if="tab === 1">
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

                    <TranslatorFilter :index="index"
                                      @kp_filter="$event => { kp_filter = $event }"
                                      @ara_filter="$event => { ara_filter = $event }"
                                      @predicate_filter="$event => { predicate_filter = $event }"
                                      @subject_category_filter="$event => { subject_category_filter = $event }"
                                      @object_category_filter="$event => { object_category_filter = $event }"
                                      ></TranslatorFilter>

                    <v-col lg>
                      <v-radio-group
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
                    <!-- <v-col :cols="data_table_current_item === null ? 'auto' : 8"> -->
                    <v-col :cols="8">
                      <v-data-table
                        :headers="_headers"
                        :items="denormalized_cells"
                        :items-per-page="-1"
                        group-by="_id"
                        class="elevation-1"
                        :search="search"
                        :custom-filter="searchMatches"
                        dense>

                        <!-- TODO: group title formatting and tooltip. potentially just put in the summary? -->
                        <template v-slot:group.summary="{ group }">
                        </template>

                        <template v-slot:item="{ item }">
                          <tr @mouseover="() => {
                                          data_table_current_item = data_table_hold_selection ? data_table_selected_item : item;
                                          }"
                              @mouseleave="() => {
                                           data_table_current_item = data_table_selected_item;
                                           }"
                              @click="() => {
                                      data_table_selected_item = data_table_hold_selection ? data_table_selected_item : item;
                                      data_table_current_item = data_table_selected_item;
                                      }">
                            <td v-for="[test, result] in Object.entries(omit('_id')({
                                       ...item,
                                       ...countResultMessages(item)
                                       }))"
                                v-bind:key="`${test}_${result}`"
                                :style="cellStyle(result.outcome)">

                              <a v-if="!!result.outcome">
                                {{ stateIcon(result.outcome) }}
                                <!-- {{ -->
                                <!-- Object.entries(result.validation) -->
                                <!-- .reduce((a, i) => { -->
                                <!-- if (!!a[i[0]]) { a[i[0]] += i[1].length } else { a[i[0]] = i[1].length } -->
                                <!--   return a -->
                                <!-- }, {}) -->
                                <!-- }} -->
                              </a>

                              <span v-else-if="test === 'spec'">
                                <v-tooltip
                                  bottom>
                                  <template v-slot:activator="{ on, attrs }">
                                    <div v-bind="attrs" v-on="on">
                                      <v-chip small outlined>{{formatCurie(result.subject_category)}}</v-chip><v-chip small outlined>{{formatCurie(result.predicate)}}</v-chip><v-chip small outlined>{{formatCurie(result.object_category)}}</v-chip>
                                    </div>
                                  </template>
                                  <b>Test Edge:</b>
                                  <span>
                                    {{ formatConcreteEdge(result) }}
                                  </span>
                                </v-tooltip>
                              </span>

                              <span v-else>
                                {{ result }}
                              </span>
                            </td>
                          </tr>
                        </template>
                      </v-data-table>
                    </v-col>
                    <v-col :cols="4">
                    <!-- <v-col :cols="4" :hidden="data_table_current_item === null"> -->
                      <v-card class="mx-auto" style="{ maxHeight: 'inherit' }">
                        <v-card-text v-if="data_table_current_item === null">
                          Hover over a row to show its test results.<br>
                          Click a row to keep its test results displayed.<br>
                          Click it again to unselect it.
                        </v-card-text>
                        <v-card-text v-else>
                          <h2>{{ formatEdge(data_table_current_item["spec"]) }}</h2><br>
                          <h3>{{ formatConcreteEdge(data_table_current_item["spec"]) }}</h3><br>
                          <v-chip-group>
                            <v-chip>Warnings: {{ selected_result_message_summary.warnings }}</v-chip>
                            <v-chip>Errors: {{ selected_result_message_summary.errors }}</v-chip>
                            <v-chip>Information: {{ selected_result_message_summary.information }}</v-chip>
                          </v-chip-group>
                          <v-treeview :items="selected_result_treeview" dense>
                            <template v-slot:prepend="{ item, open }">
                              <span v-if="!!item.data"></span>
                              <div v-else-if="!!item.outcome">
                                {{ stateIcon(item.outcome, icon_only=true) }}
                              </div>
                              <v-icon v-else-if="item.name === 'warnings'" small>
                                mdi-alert
                              </v-icon>
                              <v-icon v-else-if="item.name === 'errors'" small>
                                mdi-cancel
                              </v-icon>
                              <v-icon v-else-if="item.name === 'information'" small>
                                mdi-information
                              </v-icon>
                              <v-icon v-else-if="!!item.children && item.children.length === 0" small>
                                mdi-checkbox-blank-circle
                              </v-icon>
                            </template>
                            <template v-slot:label="{ item }">
                              <span v-if="!!item.data">
                                <ul class="noindent">
                                  <li>{{parseResultCode(item.data.code).subcode}}</li>
                                  <ul class="noindent">
                                    <li v-for="result_data in Object.entries(item.data)" v-if="result_data[0] !== 'code'" :key="hash(result_data)+Math.random()">
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
                              <span v-if="['warnings', 'errors', 'information'].includes(item.name)">
                                {{ item.children.length }}
                              </span>
                              <span v-else-if="!!!item.data">
                                {{ !!item.children && item.children.length > 0 ? item.children.reduce((a, i) => !!i.children ? a += i.children.length : a, 0) : ''}}
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

  </v-tab-item>
</v-tabs-items>
  </v-container>

<div id="app">

</div>
</v-app>
</div>
</template>

<script>
/* eslint-disable */

import jp from 'jsonpath';
import jsonQuery from 'json-query';
import hash from "object-hash";

import omit from "lodash.omit";
import pick from "lodash.pick";
import matches from "lodash.matches";
import { isObject, isArray, isString, sortBy } from "lodash";
import * as _ from "lodash";

// Components
import TranslatorFilter from "./components/TranslatorFilter/TranslatorFilter.vue"
import TranslatorCategoriesList from "./components/TranslatorCategoriesList/TranslatorCategoriesList.vue"

// Visualization
import VcPiechart from "vc-piechart";
import 'vc-piechart/dist/lib/vc-piechart.min.css';
import { Cartesian, Line, Bar } from 'laue'

// For dynamic resizing
import { SizeProvider, SizeObserver } from 'vue-size-provider'

// API code in separate file so we can switch between live and mock instance,
// also configure location for API in environment variables and build variables
import axios from "./api.js";

const MOCK = process.env.isAxiosMock;
const FEATURE_RUN_TEST_BUTTON = process.env._FEATURE_RUN_TEST_BUTTON;
const FEATURE_RUN_TEST_SELECT = process.env._FEATURE_RUN_TEST_SELECT;

export default {
    name: 'App',
    components: {
        SizeProvider,
        SizeObserver,
        TranslatorFilter,
        TranslatorCategoriesList,
        VcPiechart,
        LaCartesian: Cartesian,
        LaBar: Bar,
    },
    data() {
        return {
            MOCK,
            FEATURE_RUN_TEST_BUTTON,
            FEATURE_RUN_TEST_SELECT,
            hover: false,
            id: null,
            loading: null,
            headers: [],
            cells: [],
            token: null,
            search: '',
            tab: '',
            registryResults: [],
            kp_selections: [],
            ara_selections: [],
            test_runs_selections: [],
            kps_only: true,
            status_interval: -1,
            status: -1,
            outcome_filter: "all",
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
            resources: {},
            data_table_selected_item: null,
            data_table_current_item: null,
            data_table_hold_selection: false,
        }
    },
    created () {
        // initialize application
        if (!(this._FEATURE_RUN_TEST_BUTTON || this._FEATURE_RUN_TEST_SELECT)) {
            axios.get(`/test_runs`).then(async response => {
                const test_runs = response.data.test_runs;
                this.test_runs_selections = response.data.test_runs;
                // TODO: Feature flag
                // if (!!test_runs && test_runs.length > 0) {
                // } else {
                //   await axios.post(`/run_tests`, {}).then(response => {
                //     this.id = response.data.test_run_id;
                //     axios.get(`/test_runs`).then(response => {
                //       this.test_runs_selections = response.data.test_runs;
                //     })
                //   })
                // }
            })
        }
    },
    mounted() {
        this.$forceUpdate()
    },
    watch: {
        id(id, oldId) {
            this.loading = true;
            this.status_interval = setInterval(() => axios.get(`/status?test_run_id=${id}`).then(response => {
                this.status = response.data.percent_complete;
                if (this.status >= 100) {
                    window.clearInterval(this.status_interval)
                }
            }), 3000);
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
        index(newIndex, oldIndex) {
            if (newIndex !== null) {
                this.getAllCategories(this.id, newIndex);
            };
        }
    },
    computed: {
        selected_result_message_summary() {
            if (!!!this.data_table_current_item) {
                return {
                    "information": 0,
                    "errors": 0,
                    "warnings": 0,
                }
            }
            return this.countResultMessages(this.data_table_current_item)

        },
        selected_result_treeview() {
            if (!!!this.data_table_current_item) return []
            console.log(this.data_table_current_item)
            return Object.entries(this.data_table_current_item)
                .filter(a => !['spec', '_id', 'information', 'errors', 'warnings'].includes(a[0]))
                .map(a => ({
                    'name': a[0],
                    'outcome': a[1].outcome,
                    'children': Object.entries(a[1].validation)
                        .map(a => ({
                            'name': a[0],
                            'children': a[1]
                                .map(el => ({
                                    'name': "",
                                    'data': el,
                                }))
                        }))
                        .sort((a,b) => a.children.length <= b.children.length)
                }))
        },
        // TODO: merge these range computations into one scope
        trapi_range() {
            let trapi_versions = [];
            if (!!this.stats_summary && !_.isEmpty(this.stats_summary)) {
                trapi_versions.push(Object.entries(this.stats_summary.KP).map(([_, entry]) => entry.trapi_version));
                trapi_versions.push(Object.entries(this.stats_summary.ARA).map(([_, entry]) => entry.trapi_version));
            }
            return _(trapi_versions).flatten().uniq().omitBy(_.isUndefined).omitBy(_.isNull).sort().values()
        },
        biolink_range() {
            let biolink_versions = [];
            if (!!this.stats_summary && !_.isEmpty(this.stats_summary)) {
                biolink_versions.push(Object.entries(this.stats_summary.KP).map(([_, entry]) => entry.biolink_version));
                biolink_versions.push(Object.entries(this.stats_summary.ARA).map(([_, entry]) => entry.biolink_version));
            }
            return _(biolink_versions).flatten().uniq().omitBy(_.isUndefined).omitBy(_.isNull).sort().values();
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
                    .flatMap(provider_key => this.denormalize_provider_summary(combined_results[provider_key], provider_key));
            } else {
                return [];
            }
        },
        reduced_stats_summary() {
            return this.reduce_provider_summary(this.denormalized_stats_summary)
        },
        registryItems() {
            return this.registryResults.map(el => {
                return {
                    text: el.info.title,
                    value: el.info["x-translator"].infores,
                    component: el.info["x-translator"].component
                }
            })
        },
        _headers() {
            return this.headers
                .concat(["information", "errors", "warnings"])
                .sort(orderByArrayFunc(['spec', 'information', 'errors', 'warnings']))
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

      // sort keys
      const ___cells = __cells.map(cell =>
          Object.fromEntries(Object.entries(cell).sort(([a, _], [b, __]) => orderByArrayFunc(['spec', 'information', 'errors', 'warnings'])(a, b))));

      const denormalized_cells = ___cells
      // TODO: combine into one loop
            .filter(el => !isString(el))
            .filter(cell => Object.entries(cell).some(entry => this.outcome_filter !== "all" ? entry[1].outcome === this.outcome_filter : true))
            .filter(el => {
              return this.subject_category_filter.length > 0 ? this.subject_category_filter.includes(el.spec.subject_category) : true
                && this.predicate_filter.length > 0 ? this.predicate_filter.includes(el.spec.predicate) : true
                && this.object_category_filter > 0 ? this.object_category_filter.includes(el.spec.object_category) : true
            })
            .filter(el => this.ara_filter.length > 0 || this.kp_filter.length > 0 ?
                    _.every(this.ara_filter.concat(this.kp_filter), provider_name => _.includes(el._id, provider_name)) || _.some(this.kp_filter, kp => _.includes(el._id, kp))
                    : true);
      return this.kp_selections.length > 0 || this.ara_selections.length > 0 ?
        denormalized_cells
        .filter(cell => this.kp_selections.some(el =>
          (el.includes(cell._id)
           || this.kps_only ? el.includes(cell._id.split('|')[0]) || el.includes(cell._id.split('|')[1]) : false)
            || this.ara_selections.some(el => el.includes(cell._id.split('|')[0]) || el.includes(cell._id.split('|')[1]))))
        : denormalized_cells

    },

  },
  methods: {
    async triggerReloadTestRunSelections() {
      await axios.get(`/test_runs`).then(response => {
        this.test_runs_selections = response.data.test_runs;
      })
    },
    async triggerTestRun() {
      axios.post(`/run_tests`, {}).then(response => {
        this.id = response.data.test_run_id;
      }).then(() => {
        // refresh the test runs list
        this.triggerReloadTestRunSelections()
      })
    },
    status_color: (status) => status === "passed" ? "#00ff00"
      : status === "skipped" ? "#f0e68c"
      : status === "failed" ? "#f08080"
      : "#000000",
    denormalize_provider_summary(provider_summary, provider_key) {
      return Object.entries(provider_summary.results)
                   .flatMap((([field, value]) => Object.keys(value)
                                                       .map(i => [provider_key, field, i, value[i]])))
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
        tally[label] += value;
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
      index.KP.forEach(async kp_id => {
        await axios.get(`/resource?test_run_id=${id}&kp_id=${kp_id}`)
                   .then(response => {
                     this.resources = {
                       ...this.resources,
                       [kp_id]: response.data.summary
                     }
                     return response
                   })
                   .then(response => addFromKPs(kp_id, response.data.summary))
      });
      Object.keys(index.ARA)
            .forEach(ara_id => {
              index.ARA[ara_id].forEach(async kp_id => {
                await axios.get(`/resource?test_run_id=${id}&kp_id=${kp_id}&ara_id=${ara_id}`)
                           .then(response => {
                             this.resources = {
                               ...this.resources,
                               [ara_id+'_'+kp_id]: response.data.summary
                             }
                             return response
                           })
                           .then(response => addFromKPs(`${ara_id}_${kp_id}`, response.data.summary))
              })
            });
      // set the state directly for async updates
      // TODO: turn into incremental?
      this.subject_categories = categories.subject_category;
      this.object_categories = categories.object_category;
      this.predicates = categories.predicate;
      return categories;
    },
    flatten_ara_keys(ARAIndex, delimiter='_') {
      return Object.entries(ARAIndex).flatMap(([ara, entry]) => Object.values(entry).map(kp => ara+delimiter+kp))
    },
    makeTableData(id, stats_summary) {
      console.log("call makeTableData", id)
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
                     console.log("response")
                     if (response.status === "fulfilled") {
                       const  { headers, cells, edges, tests } = _makeTableData(response.value.resource_id, response.value.data.summary);
                       console.log("making table data", { headers, cells, edges, tests })
                       this.headers = Array.from(new Set(this.headers.concat(headers)));
                       this.cells = _.cloneDeep(this.cells).concat(cells);
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


    // import methods from packages
    hash,
    isObject,
    countBy: _.countBy,

    // custom methods for application testing
    tap: el => { console.log("hello", el, VuePursue(el)); return el },

    omit: (...keys) => object => omit(object, keys),
    pick: (...keys) => object => pick(object, keys),
    notEmpty: (list) => list.filter(el => el !== ""),

    // `custom-filter` in v-data-table props: https://vuetifyjs.com/en/api/v-data-table/#props
    searchMatches: _searchMatches,

    // adjust cell style:
    // TODO - move on to use style classes instead
    cellStyle (state) {
      // getComputedStyle(document.querySelector("td")).backgroundColor

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
        return `⚠️${!icon_only ? ' Skip' : ''}`
      } else if (state === "failed") {
        return `🚫${!icon_only ? ' Fail' : ''}`
      } else if (state === null) {
        return "NONE";
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
      return Object.entries(edge_result).reduce((acc, item) => {
        if (!!item[1] && !!item[1].validation) {
          const { validation } = item[1];
          const { information, errors, warnings } = validation;
          acc.information += information.length;
          acc.errors += errors.length;
          acc.warnings += warnings.length;
        }
        return acc
      }, {
        information: 0,
        errors: 0,
        warnings: 0,
      })
    },
    parseResultCode(code) {
      const type = code.split('.')[0]
      const subcode = code.split('.').slice(1).join('.');
      console.log(code, code.split('.'), type, subcode)
      return {
        type,
        subcode
      }
    },
    countResultMessagesByCode(resource_summary) {
      return Object.values(resource_summary.test_edges)
                   .map(e => Object.values(e.results))
                   .flatMap(i=>i)
                   .flatMap(i=>Object.values(i.validation))
                   .flatMap(i=>i)
                   .reduce((a,i)=>{
                     if (!!a[i.code]) { a[i.code] += 1 } else { a[i.code] = 1 }
                     return a
                   }, {})
    },
    groupedResultMessagesByCode(resource_summary) {
      return Object.entries(this.countResultMessagesByCode(resource_summary)).reduce((a, [code, frequency]) => {
        const { type, subcode } = this.parseResultCode(code)
        a = _.set(a, [type, subcode], frequency)
        return a
      }, {
        'warning': {},
        'error': {},
        'info': {},
      })
    },
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

// console.warn(orderByPlaceInArray([], ['spec', 'information', 'warnings', 'errors']))
// console.warn(orderByPlaceInArray(['spec', 'information', 'warnings', 'errors'], ['spec', 'information', 'warnings', 'errors']))
// console.warn(orderByPlaceInArray(['a', 'b', 'c'], ['spec', 'information', 'warnings', 'errors']))
// console.warn(orderByPlaceInArray(['spec', 'information', 'warnings', 'errors'].reverse(), ['spec', 'information', 'warnings', 'errors']))
// console.warn(orderByPlaceInArray(['spec', 'information', 'warnings', 'errors'].concat(['a', 'b', 'c']), ['spec', 'information', 'warnings', 'errors']))

// jsonpath
// queries based on schema circa Aug 5th 2022
const query_all_tests = "$.*..tests";
const query_all_results = "$.*.*.*";
const query_all_kp_results = "$.KP.*.*";
const query_all_ara_results = "$.ARA.*.*";

// recursive search function for matching string against *any* value within *any* object, array, or string within an object's hierarchy
// this behavior might require fine-tuning (should messages be searchable? should property matches be advertised?) but it's a first-pass
// for understanding what we want from our table search filtering
function _searchMatches(value, search, item) {
  return Object.entries(item).some(([key, entry]) => {
    if (isObject(entry)) {
      return _searchMatches(entry, search, entry)
    } else if (isArray(entry)) {
      return entry.some(el => _searchMatches(el, search, el))
    } else if (isString(entry)) {
      return key.toLowerCase().includes(search.toLowerCase()) || entry.toLowerCase().includes(search.toLowerCase());
    }
  })
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

Object.defineProperty(Array.prototype, 'precat', {
  configurable: true,
  writable: true,
  value: function precat() {
    return Array.prototype.concat.call([], ...arguments, this)
  }
})


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
    transform: translateY(12px);
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
    padding-left: 10px;
    padding-right: 0px;
}
</style>
